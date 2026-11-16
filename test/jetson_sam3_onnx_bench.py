#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jetson_sam3_onnx_bench.py
=========================
在 Jetson 上用 onnxruntime 单独运行 SAM3 的 ONNX 版本（如 Embedl 的 embedl_sam3_quant.onnx），
测试效果与性能。由 jetson_model_bench.py 改写：去掉 YOLO / YOLOE / PyTorch-SAM3，只保留 ONNX-SAM3。

功能
----
- 实时显示摄像头画面 + 分割结果（掩码 / 框 / 分数）+ 当前帧数
- 自动识别 ONNX 的输入 (图像 / input_ids / attention_mask) 和输出 (masks / logits / presence)，
  识别结果会打印出来；识别错了可以用 --in-* / --out-* 参数手动指定
- 文本提示的 token 只计算一次并缓存
- 加载后自动：预热 N 秒 -> 评估 M 秒 -> 输出报告（FPS、耗时、内存、CPU/GPU、温度、功耗）
- 结果保存到 bench_results/ (JSON 汇总 + 逐帧 CSV + bench_summary.csv)
- --dump-ref：保存第一帧的输入张量和原始输出 (.npz)，以后用来和 TensorRT 引擎的输出对比

依赖
----
pip install onnxruntime numpy opencv-python transformers
可选：pyrealsense2 (RealSense)、psutil
注意：pip 版 onnxruntime 在 Jetson 上只有 CPU，速度很慢，只适合验证模型和得到参考结果。

示例
----
# 第 1 步：只打印模型的输入输出，然后退出（不需要相机）
python3 jetson_sam3_onnx_bench.py --onnx embedl_sam3_quant.onnx --io-only

# 第 2 步：用一段视频测试，无界面，保存参考输出
python3 jetson_sam3_onnx_bench.py --onnx embedl_sam3_quant.onnx --prompt "tomato" \
    --source test.mp4 --no-show --dump-ref --duration 60

# RealSense 手先相机实时显示
python3 jetson_sam3_onnx_bench.py --onnx embedl_sam3_quant.onnx --prompt "tomato" \
    --source realsense --serial 230322272057

按键：[r] 重新评估  [q]/[ESC] 退出
"""

import argparse
import csv
import gc
import glob
import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

try:
    import psutil
except ImportError:
    psutil = None


# ============================================================
# 通用工具
# ============================================================
def proc_rss_mb():
    """当前进程常驻内存 (MB)"""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    if psutil:
        return psutil.Process().memory_info().rss / 1048576.0
    return float("nan")


def read_meminfo_mb():
    """系统内存 (used, total) MB。Jetson 是 CPU/GPU 共享内存，GPU 占用也算在这里"""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
        total = info["MemTotal"] / 1024.0
        avail = info.get("MemAvailable", info.get("MemFree", 0)) / 1024.0
        return total - avail, total
    except Exception:
        if psutil:
            vm = psutil.virtual_memory()
            return (vm.total - vm.available) / 1048576.0, vm.total / 1048576.0
    return float("nan"), float("nan")


def read_proc_stat():
    with open("/proc/stat") as f:
        vals = [int(x) for x in f.readline().split()[1:]]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return idle, sum(vals)


_GPU_LOAD_PATHS = None


def read_gpu_load_sysfs():
    """Jetson GPU 负载 (0-100)，读不到返回 None"""
    global _GPU_LOAD_PATHS
    if _GPU_LOAD_PATHS is None:
        cands = ["/sys/devices/gpu.0/load", "/sys/devices/platform/gpu.0/load"]
        cands += glob.glob("/sys/devices/platform/*.ga10b/load")
        cands += glob.glob("/sys/devices/platform/bus@0/*.gpu/load")
        cands += glob.glob("/sys/devices/platform/*.gv11b/load")
        _GPU_LOAD_PATHS = [p for p in cands if os.path.exists(p)]
    for p in _GPU_LOAD_PATHS:
        try:
            with open(p) as f:
                return int(f.read().strip()) / 10.0
        except Exception:
            continue
    return None


def nanmean(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return float(np.mean(xs)) if xs else None


def nanmax(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return float(np.max(xs)) if xs else None


def sigmoid(x):
    x = np.asarray(x, dtype=np.float32)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


# ============================================================
# 系统监控 (tegrastats 优先)
# ============================================================
_RE_RAM = re.compile(r"RAM (\d+)/(\d+)MB")
_RE_SWAP = re.compile(r"SWAP (\d+)/(\d+)MB")
_RE_CPU = re.compile(r"CPU \[([^\]]*)\]")
_RE_GR3D = re.compile(r"GR3D_FREQ (\d+)%")
_RE_TEMP = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)@(-?\d+(?:\.\d+)?)C\b")
_RE_PWR_IN = re.compile(r"\b(VDD_IN|POM_5V_IN|VIN_SYS_5V0|VDD_TOTAL)\s+(\d+)(?:mW)?/(\d+)")


def parse_tegrastats(line):
    s = {}
    m = _RE_RAM.search(line)
    if not m:
        return None
    s["ram_used_mb"], s["ram_total_mb"] = float(m.group(1)), float(m.group(2))
    m = _RE_SWAP.search(line)
    if m:
        s["swap_used_mb"] = float(m.group(1))
    m = _RE_CPU.search(line)
    if m:
        loads = []
        for item in m.group(1).split(","):
            item = item.strip()
            if "%" in item:
                try:
                    loads.append(float(item.split("%")[0]))
                except ValueError:
                    pass
        if loads:
            s["cpu_avg"] = float(np.mean(loads))
            s["cpu_max_core"] = float(np.max(loads))
    m = _RE_GR3D.search(line)
    if m:
        s["gpu_load"] = float(m.group(1))
    temps = {k.lower(): float(v) for k, v in _RE_TEMP.findall(line)}
    temps.pop("pmic", None)
    if temps:
        s["temp_max_c"] = max(temps.values())
        if "gpu" in temps:
            s["temp_gpu_c"] = temps["gpu"]
        if "cpu" in temps:
            s["temp_cpu_c"] = temps["cpu"]
    m = _RE_PWR_IN.search(line)
    if m:
        s["power_w"] = float(m.group(2)) / 1000.0
    return s


class SystemMonitor(threading.Thread):
    def __init__(self, interval_ms=500):
        super().__init__(daemon=True)
        self.interval_ms = interval_ms
        self.samples = deque(maxlen=50000)
        self.latest = {}
        self.lock = threading.Lock()
        self._stop_evt = threading.Event()
        self.proc = None
        self.backend = "tegrastats" if shutil.which("tegrastats") else "proc"

    def run(self):
        if self.backend == "tegrastats":
            try:
                self._run_tegrastats()
                return
            except Exception as e:
                print(f"[Monitor] tegrastats 不可用，改用 /proc: {e}")
                self.backend = "proc"
        self._run_fallback()

    def _push(self, s):
        s["t"] = time.time()
        s["proc_rss_mb"] = proc_rss_mb()
        with self.lock:
            self.samples.append(s)
            self.latest = s

    def _run_tegrastats(self):
        self.proc = subprocess.Popen(
            ["tegrastats", "--interval", str(self.interval_ms)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        got = False
        for line in self.proc.stdout:
            if self._stop_evt.is_set():
                break
            s = parse_tegrastats(line)
            if s:
                got = True
                self._push(s)
        if not got and not self._stop_evt.is_set():
            raise RuntimeError("tegrastats 没有输出")

    def _run_fallback(self):
        try:
            prev = read_proc_stat()
        except Exception:
            prev = None
        while not self._stop_evt.wait(self.interval_ms / 1000.0):
            s = {}
            s["ram_used_mb"], s["ram_total_mb"] = read_meminfo_mb()
            if prev is not None:
                cur = read_proc_stat()
                d_idle, d_total = cur[0] - prev[0], cur[1] - prev[1]
                prev = cur
                if d_total > 0:
                    s["cpu_avg"] = 100.0 * (1 - d_idle / d_total)
            g = read_gpu_load_sysfs()
            if g is not None:
                s["gpu_load"] = g
            self._push(s)

    def window(self, t0, t1):
        with self.lock:
            return [s for s in self.samples if t0 <= s["t"] <= t1]

    def get_latest(self):
        with self.lock:
            return dict(self.latest)

    def stop(self):
        self._stop_evt.set()
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass


# ============================================================
# 图像源（与原程序相同）
# ============================================================
class LiveCamera:
    """后台线程持续取帧，主线程只拿最新一帧（避免缓冲导致延迟）"""

    def __init__(self, args):
        self.args = args
        self.frame = None
        self.frame_id = -1
        self.cam_fps = 0.0
        self.stopped = False
        self.cond = threading.Condition()
        self._open()
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    def _open(self):
        a = self.args
        src = a.source
        self.rs_pipe = None
        self.cap = None
        if src.lower() == "realsense":
            import pyrealsense2 as rs
            self.rs = rs
            self.rs_pipe = rs.pipeline()
            cfg = rs.config()
            if a.serial:
                cfg.enable_device(a.serial)
            cfg.enable_stream(rs.stream.color, a.width, a.height, rs.format.bgr8, a.fps)
            self.rs_pipe.start(cfg)
            print(f"[Camera] RealSense {a.serial or '(默认设备)'} {a.width}x{a.height}@{a.fps}")
        else:
            if "!" in src:
                self.cap = cv2.VideoCapture(src, cv2.CAP_GSTREAMER)
            else:
                dev = int(src) if src.isdigit() else src
                self.cap = cv2.VideoCapture(dev, cv2.CAP_V4L2) if isinstance(dev, int) else cv2.VideoCapture(dev)
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
                self.cap.set(cv2.CAP_PROP_FPS, a.fps)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened():
                raise RuntimeError(f"无法打开相机: {src}")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[Camera] {src} {w}x{h}")

    def _grab(self):
        if self.rs_pipe is not None:
            frames = self.rs_pipe.wait_for_frames(5000)
            c = frames.get_color_frame()
            return np.asanyarray(c.get_data()).copy() if c else None
        ok, img = self.cap.read()
        return img if ok else None

    def _loop(self):
        cnt, t0 = 0, time.time()
        while not self.stopped:
            try:
                img = self._grab()
            except Exception as e:
                print(f"[Camera] 取帧失败: {e}")
                time.sleep(0.1)
                continue
            if img is None:
                time.sleep(0.01)
                continue
            with self.cond:
                self.frame = img
                self.frame_id += 1
                self.cond.notify_all()
            cnt += 1
            if time.time() - t0 >= 1.0:
                self.cam_fps = cnt / (time.time() - t0)
                cnt, t0 = 0, time.time()

    def read(self, last_id, timeout=2.0):
        with self.cond:
            self.cond.wait_for(lambda: self.frame_id != last_id or self.stopped, timeout)
            return self.frame_id, self.frame

    @property
    def ended(self):
        return False

    def release(self):
        self.stopped = True
        self.th.join(timeout=2)
        if self.rs_pipe is not None:
            try:
                self.rs_pipe.stop()
            except Exception:
                pass
        if self.cap is not None:
            self.cap.release()


class VideoFileSource:
    """视频文件：逐帧顺序读取，不丢帧，适合做可复现对比"""

    def __init__(self, path, loop=True):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频: {path}")
        self.loop = loop
        self.frame_id = -1
        self._ended = False
        self.cam_fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        print(f"[Video] {path} ({int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))} 帧)")

    def read(self, last_id, timeout=None):
        ok, img = self.cap.read()
        if not ok and self.loop:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, img = self.cap.read()
        if not ok:
            self._ended = True
            return self.frame_id, None
        self.frame_id += 1
        return self.frame_id, img

    @property
    def ended(self):
        return self._ended

    def release(self):
        self.cap.release()


class ImageFileSource:
    """单张图片：反复返回同一张图，方便和 PyTorch / TensorRT 版本逐像素对比"""

    def __init__(self, path):
        self.img = cv2.imread(path)
        if self.img is None:
            raise RuntimeError(f"无法读取图片: {path}")
        self.frame_id = -1
        self.cam_fps = 0.0
        print(f"[Image] {path} {self.img.shape[1]}x{self.img.shape[0]}")

    def read(self, last_id, timeout=None):
        self.frame_id += 1
        return self.frame_id, self.img.copy()

    @property
    def ended(self):
        return False

    def release(self):
        pass


IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


def open_source(args):
    s = args.source
    if s.lower() != "realsense" and "!" not in s and not s.isdigit() \
            and not s.startswith("/dev/") and os.path.isfile(s):
        if s.lower().endswith(IMG_EXT):
            return ImageFileSource(s)
        return VideoFileSource(s, loop=not args.no_loop)
    return LiveCamera(args)


# ============================================================
# SAM3 ONNX 推理
# ============================================================
ORT_DTYPE = {"tensor(float)": np.float32, "tensor(float16)": np.float16,
             "tensor(double)": np.float64, "tensor(int64)": np.int64,
             "tensor(int32)": np.int32, "tensor(bool)": np.bool_}

PALETTE = [(56, 56, 255), (31, 112, 255), (29, 178, 255), (49, 210, 207),
           (10, 249, 72), (23, 204, 146), (134, 219, 61), (211, 188, 0),
           (255, 115, 100), (236, 24, 0), (255, 56, 132), (199, 55, 255)]


def build_providers(choice, ort):
    avail = ort.get_available_providers()
    if choice == "cpu":
        want = ["CPUExecutionProvider"]
    elif choice == "cuda":
        want = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:  # auto：有 CUDA 用 CUDA。故意不用 TensorRT EP（它依赖系统的 TRT 8.6，和直接转 engine 是同一个问题）
        want = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in avail]
    for p in want:
        if p not in avail:
            print(f"[ORT] 警告: {p} 不可用 (可用: {avail})")
    return [p for p in want if p in avail] or ["CPUExecutionProvider"]


def describe_io(sess):
    print("\n=== ONNX 输入 ===")
    for i in sess.get_inputs():
        print(f"  {i.name:<30} {str(i.shape):<28} {i.type}")
    print("=== ONNX 输出 ===")
    for o in sess.get_outputs():
        print(f"  {o.name:<30} {str(o.shape):<28} {o.type}")
    print()


class TextTokenizer:
    """SAM3 的文本编码使用 CLIP BPE 词表。依次尝试 --tokenizer 里的来源"""

    def __init__(self, sources, max_len):
        from transformers import AutoTokenizer
        last_err = None
        self.tok = None
        for src in sources:
            try:
                self.tok = AutoTokenizer.from_pretrained(src)
                print(f"[Tokenizer] 使用 {src}")
                break
            except Exception as e:
                last_err = e
                print(f"[Tokenizer] {src} 加载失败: {type(e).__name__}: {str(e)[:120]}")
        if self.tok is None:
            raise RuntimeError(f"所有 tokenizer 来源都加载失败: {last_err}")
        self.max_len = max_len

    def __call__(self, text):
        enc = self.tok([text], padding="max_length", max_length=self.max_len,
                       truncation=True, return_tensors="np")
        return enc["input_ids"], enc["attention_mask"]


class SegResult:
    """简单的结果对象：dets = [{label, score, mask(bool HxW), box(x1,y1,x2,y2)}]"""

    def __init__(self, img, dets, labels):
        self.img = img
        self.dets = dets
        self.labels = labels

    def __len__(self):
        return len(self.dets)

    def plot(self, alpha=0.45):
        vis = self.img.copy()
        for d in self.dets:
            color = PALETTE[self.labels.index(d["label"]) % len(PALETTE)]
            m = d["mask"]
            vis[m] = (vis[m] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
            cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis, cnts, -1, color, 2)
            x1, y1, x2, y2 = d["box"]
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 1)
            txt = f"{d['label']} {d['score']:.2f}"
            cv2.putText(vis, txt, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        color, 2, cv2.LINE_AA)
        return vis


class Sam3OnnxRunner:
    kind = "sam3_onnx"

    def __init__(self, path, args):
        import onnxruntime as ort
        self.args = args
        self.name = os.path.basename(path)
        self.prompts = [p.strip() for p in args.prompt.split(",") if p.strip()]

        so = ort.SessionOptions()
        so.log_severity_level = 3
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.intra_op_num_threads = args.threads or (os.cpu_count() or 4)
        providers = build_providers(args.provider, ort)
        print(f"[ORT] onnxruntime {ort.__version__}, 请求 provider: {providers}")
        t0 = time.perf_counter()
        self.sess = ort.InferenceSession(path, so, providers=providers)
        print(f"[ORT] 会话创建 {time.perf_counter() - t0:.1f}s, 实际 provider: {self.sess.get_providers()}")
        describe_io(self.sess)

        self._map_inputs()
        self.out_names = [o.name for o in self.sess.get_outputs()]
        self.out_map = None  # 第一次推理时根据实际形状确定

        # 图像尺寸：模型里是固定数字就用模型的，否则用 --size
        shp = self.in_image.shape
        self.H = shp[2] if isinstance(shp[2], int) else args.size
        self.W = shp[3] if isinstance(shp[3], int) else args.size
        self.img_dtype = ORT_DTYPE.get(self.in_image.type, np.float32)
        self.mean = np.array(args.mean, dtype=np.float32).reshape(1, 1, -1)
        self.std = np.array(args.std, dtype=np.float32).reshape(1, 1, -1)
        print(f"[Pre] 图像输入 '{self.in_image.name}' -> {self.W}x{self.H}, "
              f"mean={args.mean}, std={args.std}, dtype={self.img_dtype.__name__}")

        # 文本 token：只算一次并缓存
        self.text_feeds = {}
        if self.in_ids is not None:
            L = self.in_ids.shape[1] if len(self.in_ids.shape) > 1 and isinstance(self.in_ids.shape[1], int) \
                else args.max_text_len
            tok = TextTokenizer(args.tokenizer, L)
            for p in self.prompts:
                ids, mask = tok(p)
                if self.in_mask is None and args.pad_id >= 0:
                    # 模型没有 attention_mask 输入时，原版 SAM3 用 0 填充并靠 (token != 0) 判断有效位置，
                    # 而 HF 的 CLIP tokenizer 默认用 49407 填充，这里统一改成 --pad-id
                    ids = ids.copy()
                    ids[mask == 0] = args.pad_id
                feed = {self.in_ids.name: ids.astype(ORT_DTYPE.get(self.in_ids.type, np.int64))}
                if self.in_mask is not None:
                    feed[self.in_mask.name] = mask.astype(ORT_DTYPE.get(self.in_mask.type, np.int64))
                self.text_feeds[p] = feed
                n_tok = int(mask.sum())
                print(f"[Text] '{p}' -> {n_tok} tokens (长度 {L}): {ids[0, :min(n_tok + 1, L)].tolist()}")
        else:
            print("[Text] 模型没有文本输入，--prompt 只作为显示用的标签")
            self.text_feeds = {self.prompts[0] if self.prompts else "object": {}}
            self.prompts = list(self.text_feeds)

        self.dumped = False

    # ---------- 输入映射 ----------
    def _map_inputs(self):
        a = self.args
        ins = {i.name: i for i in self.sess.get_inputs()}
        self.in_image = self.in_ids = self.in_mask = None
        if a.in_image:
            self.in_image = ins[a.in_image]
        if a.in_ids:
            self.in_ids = ins[a.in_ids]
        if a.in_mask:
            self.in_mask = ins[a.in_mask]
        used = {x.name for x in (self.in_image, self.in_ids, self.in_mask) if x is not None}
        for i in ins.values():
            if i.name in used:
                continue
            n = i.name.lower()
            is_float = "float" in i.type
            if self.in_image is None and is_float and len(i.shape) == 4:
                self.in_image = i
            elif self.in_mask is None and "mask" in n and not is_float:
                self.in_mask = i
            elif self.in_ids is None and not is_float and len(i.shape) == 2:
                self.in_ids = i
            else:
                raise RuntimeError(
                    f"无法自动识别输入 '{i.name}' {i.shape} {i.type}。"
                    f"请用 --in-image / --in-ids / --in-mask 手动指定，并把上面的输入输出列表发给我")
        if self.in_image is None:
            raise RuntimeError("没有找到 4 维浮点图像输入，请用 --in-image 指定")
        print(f"[Map] image='{self.in_image.name}', ids='{getattr(self.in_ids, 'name', None)}', "
              f"mask='{getattr(self.in_mask, 'name', None)}'")

    # ---------- 输出映射（第一次推理时） ----------
    def _map_outputs(self, outs):
        a = self.args
        arr = dict(zip(self.out_names, outs))
        mk, lk, pk = a.out_masks, a.out_logits, a.out_presence
        if mk is None:
            cands = [n for n, v in arr.items() if v.ndim == 4 and v.shape[-1] >= 16 and v.shape[-2] >= 16]
            if not cands:
                cands = [n for n, v in arr.items() if v.ndim == 3 and v.shape[-1] >= 16 and v.shape[-2] >= 16]
            if not cands:
                raise RuntimeError("找不到掩码输出，请用 --out-masks 指定")
            mk = max(cands, key=lambda n: arr[n].size)
        Q = arr[mk].shape[1] if arr[mk].ndim == 4 else arr[mk].shape[0]
        if pk is None:
            c = [n for n in arr if "presence" in n.lower()]
            pk = c[0] if c else None
        if lk is None:
            c = [n for n, v in arr.items() if n not in (mk, pk) and "logit" in n.lower()
                 and v.ndim >= 2 and v.shape[1] == Q]
            if not c:  # 按形状找 (B,Q) 或 (B,Q,1)
                c = [n for n, v in arr.items() if n not in (mk, pk)
                     and (v.ndim == 2 and v.shape[1] == Q or v.ndim == 3 and v.shape[1] == Q and v.shape[2] <= 2)]
            lk = c[0] if c else None
        self.out_map = {"masks": mk, "logits": lk, "presence": pk}
        print(f"[Map] 输出: masks='{mk}' {arr[mk].shape}, logits='{lk}' "
              f"{arr[lk].shape if lk else ''}, presence='{pk}' {arr[pk].shape if pk else ''}")
        if lk is None:
            print("[Map] 警告: 没找到分数输出，所有 query 的分数按 1.0 处理（会出现大量掩码），请用 --out-logits 指定")

    # ---------- 前处理 / 后处理 ----------
    def preprocess(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(rgb, (self.W, self.H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        img = (img - self.mean) / self.std
        return np.ascontiguousarray(img.transpose(2, 0, 1)[None]).astype(self.img_dtype)

    def postprocess(self, outs, frame, label):
        arr = dict(zip(self.out_names, outs))
        masks = arr[self.out_map["masks"]]
        masks = masks[0] if masks.ndim == 4 else masks          # (Q, h, w) logits
        Q = masks.shape[0]
        if self.out_map["logits"]:
            lg = arr[self.out_map["logits"]][0].astype(np.float32)
            if lg.ndim > 1:
                lg = lg.max(axis=-1)
            scores = sigmoid(lg[:Q])
        else:
            scores = np.ones(Q, np.float32)
        if self.out_map["presence"]:
            scores = scores * float(sigmoid(arr[self.out_map["presence"]].reshape(-1)[0]))

        h, w = frame.shape[:2]
        dets = []
        for q in np.where(scores >= self.args.sam_conf)[0]:
            m = cv2.resize(masks[q].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > self.args.mask_thr
            if m.sum() < self.args.min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(m.astype(np.uint8))
            dets.append(dict(label=label, score=float(scores[q]), mask=m, box=(x, y, x + bw, y + bh)))
        dets.sort(key=lambda d: -d["score"])
        return dets

    def infer(self, frame):
        t0 = time.perf_counter()
        x = self.preprocess(frame)
        t1 = time.perf_counter()
        all_dets, run_ms, raw = [], 0.0, {}
        for p in self.prompts:
            feeds = {self.in_image.name: x, **self.text_feeds[p]}
            ta = time.perf_counter()
            outs = self.sess.run(None, feeds)
            run_ms += (time.perf_counter() - ta) * 1000.0
            if self.out_map is None:
                self._map_outputs(outs)
            all_dets += self.postprocess(outs, frame, p)
            if self.args.dump_ref and not self.dumped:
                raw[p] = (feeds, outs)
        t2 = time.perf_counter()
        if raw:
            self._dump(frame, raw)
        detail = {"sam_pre_ms": (t1 - t0) * 1000.0, "sam_run_ms": run_ms,
                  "sam_post_ms": (t2 - t1) * 1000.0 - run_ms}
        return SegResult(frame, all_dets, self.prompts), (t2 - t0) * 1000.0, detail

    def _dump(self, frame, raw):
        os.makedirs(self.args.out, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(self.args.out, f"onnx_ref_{stamp}")
        cv2.imwrite(base + "_frame.png", frame)
        data = {}
        for k, (p, (feeds, outs)) in enumerate(raw.items()):
            for n, v in feeds.items():
                data[f"p{k}_in_{n}"] = v
            for n, v in zip(self.out_names, outs):
                data[f"p{k}_out_{n}"] = v
        np.savez_compressed(base + ".npz", prompts=np.array(list(raw)), **data)
        print(f"[Dump] 参考输入/输出已保存: {base}.npz / _frame.png")
        self.dumped = True

    def close(self):
        del self.sess


def count_dets(r):
    return 0 if r is None else len(r)


def load_runner(args, sample_frame):
    print(f"\n[Load] 加载 SAM3 ONNX: {args.onnx}")
    gc.collect()
    ram0, _ = read_meminfo_mb()
    rss0 = proc_rss_mb()
    t0 = time.perf_counter()
    runner = Sam3OnnxRunner(args.onnx, args)
    print("[Load] 首次推理（计入加载时间，CPU 上可能要几十秒）...")
    r, ms, _ = runner.infer(sample_frame)
    load_s = time.perf_counter() - t0
    print(f"[Load] 首次推理 {ms / 1000:.1f}s, 检测到 {count_dets(r)} 个目标")
    time.sleep(0.5)
    ram1, _ = read_meminfo_mb()
    info = dict(load_time_s=load_s, load_ram_delta_mb=ram1 - ram0,
                load_rss_delta_mb=proc_rss_mb() - rss0)
    print(f"[Load] 完成 {load_s:.1f}s, 系统内存 +{info['load_ram_delta_mb']:.0f} MB, "
          f"进程RSS +{info['load_rss_delta_mb']:.0f} MB")
    return runner, info


# ============================================================
# 评估
# ============================================================
class EvalSession:
    def __init__(self, runner, load_info, warmup_s, duration_s, min_frames):
        self.kind, self.name = runner.kind, runner.name
        self.load_info = load_info
        self.warmup_s, self.duration_s, self.min_frames = warmup_s, duration_s, min_frames
        self.t_create = time.time()
        self.state = "warmup"
        self.t_start = self.t_end = None
        self.frames = []
        self.reported = False

    def update(self, rec):
        now = rec["t"]
        if self.state == "warmup" and now - self.t_create >= self.warmup_s:
            self.state = "running"
            self.t_start = now - rec["loop_dt_ms"] / 1000.0  # 慢模型时把这一帧的时间也算进去
        if self.state == "running":
            self.frames.append(rec)
            if now - self.t_start >= self.duration_s and len(self.frames) >= self.min_frames:
                self.state = "done"
                self.t_end = now
                return True
        return False

    def status_text(self):
        now = time.time()
        if self.state == "warmup":
            return f"WARMUP {max(0, self.warmup_s - (now - self.t_create)):.1f}s", 0.0
        if self.state == "running":
            el = now - self.t_start
            return f"EVAL {el:.0f}/{self.duration_s:.0f}s  ({len(self.frames)} frames)", min(1.0, el / self.duration_s)
        return "EVAL DONE  (r: re-run)", 1.0


def summarize(sess, monitor, baseline, partial=False):
    fr = sess.frames
    if len(fr) < 1:
        return None
    t_end = sess.t_end or fr[-1]["t"]
    span = max(1e-6, t_end - sess.t_start)
    infer = np.array([f["infer_ms"] for f in fr])
    loop_dt = np.array([f["loop_dt_ms"] for f in fr])
    inst_fps = 1000.0 / np.clip(loop_dt, 1e-3, None)
    sys_s = monitor.window(sess.t_start, t_end)

    def col(k):
        return [s.get(k) for s in sys_s]

    ram_avg, ram_peak = nanmean(col("ram_used_mb")), nanmax(col("ram_used_mb"))
    out = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "partial": partial,
        "model_kind": sess.kind,
        "model_name": sess.name,
        "provider": ",".join(sess.providers) if hasattr(sess, "providers") else None,
        "eval_seconds": round(span, 2),
        "frames": len(fr),
        "pipeline_fps_avg": len(fr) / span,
        "pipeline_fps_min": float(np.min(inst_fps)),
        "pipeline_fps_p5": float(np.percentile(inst_fps, 5)),
        "infer_fps_avg": 1000.0 / float(np.mean(infer)),
        "infer_ms_mean": float(np.mean(infer)),
        "infer_ms_p50": float(np.percentile(infer, 50)),
        "infer_ms_p95": float(np.percentile(infer, 95)),
        "infer_ms_max": float(np.max(infer)),
        "infer_ms_std": float(np.std(infer)),
        "detections_avg": float(np.mean([f["n_det"] for f in fr])),
        "ram_total_mb": nanmax(col("ram_total_mb")),
        "ram_baseline_mb": baseline["ram_used_mb"],
        "ram_used_avg_mb": ram_avg,
        "ram_used_peak_mb": ram_peak,
        "ram_increase_vs_baseline_mb": (ram_peak - baseline["ram_used_mb"]) if ram_peak else None,
        "swap_used_peak_mb": nanmax(col("swap_used_mb")),
        "proc_rss_avg_mb": nanmean(col("proc_rss_mb")),
        "proc_rss_peak_mb": nanmax(col("proc_rss_mb")),
        "cpu_avg_pct": nanmean(col("cpu_avg")),
        "cpu_max_core_pct": nanmax(col("cpu_max_core")),
        "gpu_avg_pct": nanmean(col("gpu_load")),
        "gpu_max_pct": nanmax(col("gpu_load")),
        "temp_max_c": nanmax(col("temp_max_c")),
        "temp_gpu_max_c": nanmax(col("temp_gpu_c")),
        "power_avg_w": nanmean(col("power_w")),
        "power_max_w": nanmax(col("power_w")),
        "monitor_backend": monitor.backend,
        "monitor_samples": len(sys_s),
    }
    detail_keys = sorted({k for f in fr for k in f if k.startswith("sam_")})
    for k in detail_keys:
        out[k.replace("_ms", "_ms_mean")] = nanmean([f.get(k) for f in fr])
    out.update(sess.load_info)
    return out


def fmt(v, unit="", nd=1):
    if v is None:
        return "N/A"
    return f"{v:.{nd}f}{unit}"


def print_report(rep):
    tag = " (中途结束，部分数据)" if rep["partial"] else ""
    print("\n" + "=" * 64)
    print(f" 评估报告{tag}: [{rep['model_kind'].upper()}] {rep['model_name']}  ({rep.get('provider')})")
    print("=" * 64)
    print(f" 评估时长 / 帧数        : {rep['eval_seconds']:.1f} s / {rep['frames']} 帧")
    print(f" 实际平均 FPS (含相机)  : {fmt(rep['pipeline_fps_avg'], nd=2)}   (最低 {fmt(rep['pipeline_fps_min'], nd=2)})")
    print(f" 纯推理 FPS             : {fmt(rep['infer_fps_avg'], nd=2)}")
    print(f" 推理耗时 mean/p50/p95/max : {fmt(rep['infer_ms_mean'])} / {fmt(rep['infer_ms_p50'])} / "
          f"{fmt(rep['infer_ms_p95'])} / {fmt(rep['infer_ms_max'])} ms")
    for k, v in rep.items():
        if k.startswith("sam_"):
            print(f"   - {k:<22}: {fmt(v, ' ms')}")
    print(f" 平均检测数             : {fmt(rep['detections_avg'], nd=2)}")
    print(f" 模型加载时间           : {fmt(rep['load_time_s'], ' s')}  (加载时系统内存 +{fmt(rep['load_ram_delta_mb'], ' MB', 0)})")
    print(f" 系统内存 avg / peak    : {fmt(rep['ram_used_avg_mb'], '', 0)} / {fmt(rep['ram_used_peak_mb'], '', 0)} MB  "
          f"(总 {fmt(rep['ram_total_mb'], '', 0)} MB, 比加载模型前 +{fmt(rep['ram_increase_vs_baseline_mb'], '', 0)} MB)")
    print(f" SWAP peak              : {fmt(rep['swap_used_peak_mb'], ' MB', 0)}")
    print(f" 进程 RSS avg / peak    : {fmt(rep['proc_rss_avg_mb'], '', 0)} / {fmt(rep['proc_rss_peak_mb'], ' MB', 0)}")
    print(f" CPU 平均 / 最忙核心    : {fmt(rep['cpu_avg_pct'], '%')} / {fmt(rep['cpu_max_core_pct'], '%')}")
    print(f" GPU 平均 / 峰值        : {fmt(rep['gpu_avg_pct'], '%')} / {fmt(rep['gpu_max_pct'], '%')}")
    print(f" 温度最高 (GPU)         : {fmt(rep['temp_max_c'], ' C')} ({fmt(rep['temp_gpu_max_c'], ' C')})")
    print(f" 功耗 avg / max         : {fmt(rep['power_avg_w'], ' W', 2)} / {fmt(rep['power_max_w'], ' W', 2)}")
    print("=" * 64 + "\n")


def save_report(rep, sess, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(out_dir, f"{stamp}_{sess.kind}_{os.path.splitext(sess.name)[0]}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    keys = sorted({k for fr in sess.frames for k in fr})
    with open(base + "_frames.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(sess.frames)
    summ = os.path.join(out_dir, "bench_summary.csv")
    new = not os.path.exists(summ)
    with open(summ, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rep.keys()), extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(rep)
    print(f"[Save] {base}.json / _frames.csv, 汇总追加到 {summ}")


def finish_session(sess, monitor, baseline, out_dir, partial=False):
    if sess is None or sess.reported or sess.t_start is None:
        return
    rep = summarize(sess, monitor, baseline, partial=partial)
    if rep is None:
        return
    sess.reported = True
    print_report(rep)
    save_report(rep, sess, out_dir)


# ============================================================
# 显示
# ============================================================
def draw_hud(img, lines, progress):
    h, w = img.shape[:2]
    scale = max(0.5, min(1.0, w / 1280.0))
    lh = int(26 * scale + 6)
    box_h = lh * len(lines) + 18
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (int(620 * scale) + 40, box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)
    for i, (txt, color) in enumerate(lines):
        cv2.putText(img, txt, (10, 10 + lh * (i + 1) - 6), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6 * scale + 0.1, color, 2 if i < 2 else 1, cv2.LINE_AA)
    bw = int(620 * scale)
    cv2.rectangle(img, (10, box_h - 8), (10 + bw, box_h - 2), (80, 80, 80), -1)
    cv2.rectangle(img, (10, box_h - 8), (10 + int(bw * progress), box_h - 2), (0, 200, 255), -1)
    return img


def render(frame, r, runner, stats, mon, sess, cam_fps):
    vis = r.plot() if r is not None else frame.copy()
    st, prog = sess.status_text()

    def g(k, nd=0):
        v = mon.get(k)
        return "--" if v is None else f"{v:.{nd}f}"

    lines = [
        (f"SAM3-ONNX: {runner.name}", (0, 255, 255)),
        (f"FPS {stats['fps_ema']:5.2f}   infer {stats['infer_ema']:7.1f} ms", (0, 255, 0)),
        (f"Detections: {stats['n_det']}   Camera: {cam_fps:4.1f} fps", (255, 255, 255)),
        (f"RAM {g('ram_used_mb')}/{g('ram_total_mb')} MB  RSS {g('proc_rss_mb')} MB", (255, 255, 255)),
        (f"GPU {g('gpu_load')}%  CPU {g('cpu_avg')}%  Temp {g('temp_max_c', 1)}C  Pwr {g('power_w', 2)}W", (255, 255, 255)),
        (st, (0, 200, 255)),
        ("[r] re-eval  [q] quit", (180, 180, 180)),
    ]
    return draw_hud(vis, lines, prog)


# ============================================================
# 主程序
# ============================================================
def parse_args():
    p = argparse.ArgumentParser(description="Jetson SAM3 (ONNX / onnxruntime) 性能与效果测试",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--onnx", required=True, help="SAM3 ONNX 模型 (.onnx.data 需放在同一目录)")
    p.add_argument("--io-only", action="store_true", help="只打印模型输入输出后退出")
    # 图像源
    p.add_argument("--source", default="realsense",
                   help="realsense / 相机编号(0) / /dev/videoX / 视频文件 / 图片 / GStreamer 管线")
    p.add_argument("--serial", default=None, help="RealSense 序列号 (手先: 230322272057)")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--no-loop", action="store_true", help="视频文件播完不循环")
    # SAM3
    p.add_argument("--prompt", default="tomato", help="文本提示，多个用逗号分隔（每个提示单独跑一次模型）")
    p.add_argument("--sam-conf", type=float, default=0.4, help="分数阈值")
    p.add_argument("--mask-thr", type=float, default=0.0, help="掩码 logit 阈值 (0 = 概率 0.5)")
    p.add_argument("--min-area", type=int, default=20, help="小于这个像素数的掩码丢弃")
    p.add_argument("--size", type=int, default=924, help="模型输入是动态尺寸时使用的边长 (Embedl 版为 924)")
    p.add_argument("--mean", type=float, nargs=3, default=[0.5, 0.5, 0.5])
    p.add_argument("--std", type=float, nargs=3, default=[0.5, 0.5, 0.5])
    p.add_argument("--max-text-len", type=int, default=32, help="文本输入是动态长度时使用的 token 长度")
    p.add_argument("--pad-id", type=int, default=0,
                   help="模型没有 attention_mask 输入时，填充位置使用的 token id (原版 SAM3 为 0；-1 = 用 tokenizer 默认值)")
    p.add_argument("--tokenizer", nargs="+", default=["facebook/sam3", "openai/clip-vit-base-patch32"],
                   help="tokenizer 来源 (HF 名称或本地路径)，按顺序尝试")
    # 手动指定输入输出名（自动识别失败时）
    p.add_argument("--in-image", default=None)
    p.add_argument("--in-ids", default=None)
    p.add_argument("--in-mask", default=None)
    p.add_argument("--out-masks", default=None)
    p.add_argument("--out-logits", default=None)
    p.add_argument("--out-presence", default=None)
    # onnxruntime
    p.add_argument("--provider", choices=["auto", "cpu", "cuda"], default="auto",
                   help="auto: 有 CUDAExecutionProvider 就用，否则 CPU")
    p.add_argument("--threads", type=int, default=0, help="CPU 线程数，0 = 全部核心")
    p.add_argument("--dump-ref", action="store_true", help="保存第一帧的输入和原始输出 (.npz)，用于和 TensorRT 对比")
    # 通用
    p.add_argument("--warmup", type=float, default=0.0, help="预热秒数（不计入评估；ONNX-CPU 很慢，默认不预热）")
    p.add_argument("--duration", type=float, default=60.0, help="评估秒数")
    p.add_argument("--min-frames", type=int, default=3, help="评估至少要的帧数（慢模型时会超过 --duration）")
    p.add_argument("--monitor-interval", type=int, default=500, help="系统监控采样间隔 ms")
    p.add_argument("--no-show", action="store_true", help="不显示画面，评估完自动退出")
    p.add_argument("--exit-after-eval", action="store_true", help="评估完成后退出")
    p.add_argument("--display-width", type=int, default=1280, help="显示窗口最大宽度")
    p.add_argument("--out", default="bench_results", help="结果保存目录")
    a = p.parse_args()
    if not os.path.exists(a.onnx):
        p.error(f"找不到文件: {a.onnx}")
    data = a.onnx + ".data"
    if not os.path.exists(data):
        print(f"[警告] 没找到 {data}。如果模型使用外部权重，加载会失败")
    if a.no_show:
        a.exit_after_eval = True
    return a


def main():
    args = parse_args()

    if args.io_only:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.log_severity_level = 3
        print(f"[ORT] onnxruntime {ort.__version__}, 可用 provider: {ort.get_available_providers()}")
        t0 = time.perf_counter()
        sess = ort.InferenceSession(args.onnx, so, providers=["CPUExecutionProvider"])
        print(f"[ORT] 加载 {time.perf_counter() - t0:.1f}s")
        describe_io(sess)
        return

    monitor = SystemMonitor(args.monitor_interval)
    monitor.start()
    print(f"[Monitor] 后端: {monitor.backend}")

    source = open_source(args)
    fid, first = -1, None
    for _ in range(50):
        fid, first = source.read(-1, timeout=2.0)
        if first is not None:
            break
    if first is None:
        print("取不到图像，退出")
        source.release()
        monitor.stop()
        return

    time.sleep(1.0)
    ram_used, ram_total = read_meminfo_mb()
    baseline = {"ram_used_mb": ram_used, "proc_rss_mb": proc_rss_mb()}
    print(f"[Baseline] 系统内存 {ram_used:.0f}/{ram_total:.0f} MB, 进程 RSS {baseline['proc_rss_mb']:.0f} MB")

    try:
        runner, load_info = load_runner(args, first)
    except BaseException:
        source.release()
        monitor.stop()
        raise

    def new_session():
        s = EvalSession(runner, load_info, args.warmup, args.duration, args.min_frames)
        s.providers = runner.sess.get_providers()
        return s

    sess = new_session()
    stats = {"fps_ema": 0.0, "infer_ema": 0.0, "n_det": 0}

    show = not args.no_show
    win = "Jetson SAM3 ONNX Bench"
    if show:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last_id = fid
    t_prev = time.perf_counter()
    try:
        while True:
            fid, frame = source.read(last_id, timeout=2.0)
            if frame is None:
                if source.ended:
                    print("视频结束")
                    break
                continue
            if fid == last_id:
                continue
            last_id = fid

            r, infer_ms, detail = runner.infer(frame)
            now = time.perf_counter()
            loop_dt = now - t_prev
            t_prev = now
            n_det = count_dets(r)

            a = 0.2
            stats["fps_ema"] = (1 / loop_dt) if stats["fps_ema"] == 0 else (1 - a) * stats["fps_ema"] + a / loop_dt
            stats["infer_ema"] = infer_ms if stats["infer_ema"] == 0 else (1 - a) * stats["infer_ema"] + a * infer_ms
            stats["n_det"] = n_det
            print(f"[Frame {fid}] infer {infer_ms:8.1f} ms, 检测 {n_det}")

            rec = {"t": time.time(), "frame_id": fid, "infer_ms": infer_ms,
                   "loop_dt_ms": loop_dt * 1000.0, "n_det": n_det, **detail}
            if sess.update(rec):
                finish_session(sess, monitor, baseline, args.out)
                if args.exit_after_eval:
                    break

            if show:
                vis = render(frame, r, runner, stats, monitor.get_latest(), sess,
                             getattr(source, "cam_fps", 0.0))
                if vis.shape[1] > args.display_width:
                    s = args.display_width / vis.shape[1]
                    vis = cv2.resize(vis, None, fx=s, fy=s)
                cv2.imshow(win, vis)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                elif key == ord("r"):
                    finish_session(sess, monitor, baseline, args.out, partial=True)
                    sess = new_session()
                    print("[Eval] 重新开始评估")
    except KeyboardInterrupt:
        print("\nCtrl+C")
    finally:
        finish_session(sess, monitor, baseline, args.out, partial=(sess.state != "done"))
        source.release()
        monitor.stop()
        if show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
