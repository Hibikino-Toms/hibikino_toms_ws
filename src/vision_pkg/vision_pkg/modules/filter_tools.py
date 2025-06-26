"""
@authored by ogawa, 小川
------------
Retinex-based image enhancement filters
RetinexフィルタであるSSR, MSR, MSRCRの実装

2024/9/22 時点
呼び出してカメラでフィルターをかけながらみれることを確認

"""


import cv2
import numpy as np

class Filter_SSR:
    """Single Scale Retinex (SSR) フィルタ"""
    
    @staticmethod
    def gauss_blur(img, sigma):
        """ガウスフィルタを適用する関数"""
        ksize = int(6 * sigma + 1)
        return cv2.GaussianBlur(img, (ksize, ksize), sigma)

    @staticmethod
    def retinex_filter(img, params):
        """SSR アルゴリズムを適用する統一された関数"""
        sigma = params[0] if params else 250  # パラメータが指定されない場合はデフォルト値を使用
        img = img.astype('float32') + 1
        ret = np.zeros_like(img)
        for i in range(img.shape[-1]):
            channel = img[..., i]
            blurred = Filter_SSR.gauss_blur(channel, sigma)
            ret[..., i] = np.log(channel) - np.log(blurred + 1)
        mmin = np.min(ret)
        mmax = np.max(ret)
        ret = np.clip((ret - mmin) / (mmax - mmin) * 255, 0, 255)
        return ret.astype('uint8')


class Filter_MSR:
    """Multi-scale Retinex (MSR) フィルタ"""
    
    @staticmethod
    def gauss_blur(img, sigma):
        """ガウスフィルタを適用する関数"""
        ksize = int(6 * sigma + 1)
        return cv2.GaussianBlur(img, (ksize, ksize), sigma)

    @staticmethod
    def ssr(img, sigma):
        """Single Scale Retinex (SSR) を適用する補助関数"""
        img_log = np.log1p(np.array(img, dtype="float") / 255)
        blur = Filter_MSR.gauss_blur(img_log, sigma)
        retinex = np.exp(img_log - blur) - 1
        return retinex

    @staticmethod
    def retinex_filter(img, params):
        """MSR アルゴリズムを適用する統一された関数"""
        sigma_scales = params if params else [15, 80, 250]  # パラメータが指定されない場合のデフォルトスケール
        msr = np.zeros_like(img, dtype=float)
        for sigma in sigma_scales:
            msr += Filter_MSR.ssr(img, sigma)
        msr = msr / len(sigma_scales)
        msr = (msr - np.min(msr)) / (np.max(msr) - np.min(msr)) * 255
        return msr.astype(np.uint8)


class Filter_MSRCR:
    """MSRCR (Multi-scale Retinex with Color Restoration) フィルタ"""
    
    @staticmethod
    def gauss_blur(img, sigma):
        """ガウスフィルタを適用する関数"""
        ksize = int(6 * sigma + 1)
        return cv2.GaussianBlur(img, (ksize, ksize), sigma)

    @staticmethod
    def color_balance(img, low_per, high_per):
        """色のバランス調整を行う関数"""
        tot_pix = img.shape[1] * img.shape[0]
        low_count = tot_pix * low_per / 100
        high_count = tot_pix * (100 - high_per) / 100
        ch_list = [img] if len(img.shape) == 2 else cv2.split(img)
        cs_img = []

        for ch in ch_list:
            cum_hist_sum = np.cumsum(cv2.calcHist([ch], [0], None, [256], (0, 256)))
            li, hi = np.searchsorted(cum_hist_sum, (low_count, high_count))
            if li == hi:
                cs_img.append(ch)
                continue
            lut = np.array([0 if i < li else (255 if i > hi else round((i - li) / (hi - li) * 255)) for i in range(256)], dtype='uint8')
            cs_ch = cv2.LUT(ch, lut)
            cs_img.append(cs_ch)

        return cv2.merge(cs_img) if len(cs_img) > 1 else np.squeeze(cs_img)

    @staticmethod
    def retinex_filter(img, params):
        """MSRCR アルゴリズムを適用する統一された関数"""
        sigmas = params.get("sigmas", [15, 80, 250])  # デフォルトのシグマ値
        alpha = params.get("alpha", 125)
        beta = params.get("beta", 46)
        G = params.get("G", 192)
        b = params.get("b", -30)
        low_per = params.get("low_per", 1)
        high_per = params.get("high_per", 1)

        img = img.astype(np.float64) + 1.0
        msr = np.zeros_like(img)
        for sigma in sigmas:
            blurred = Filter_MSRCR.gauss_blur(img, sigma)
            msr += np.log(img / (blurred + 1))
        msr *= beta * np.log(alpha * img)
        msr = G * msr + b
        msr = cv2.normalize(msr, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8UC3)
        balanced_msr = Filter_MSRCR.color_balance(msr, low_per, high_per)
        return balanced_msr.astype('uint8')
