from ultralytics import YOLO
import yaml

def export_model(weight):
    # Load a YOLO11n PyTorch model
    model = YOLO(weight)
    # Export the model to TensorRT
    model.export(format="engine", device="0", workspace=2, half=True)  # creates '~.engine'

def load_yaml(file_path):
    """YAMLファイルを読み込むヘルパー関数"""
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"YAMLファイルの解析エラー: {e}")

def main():
    # パラメータ設定用のyamlファイル
    yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
    # YAMLファイルの読み込み
    params = load_yaml(yaml_path)
    vision_params = params["vision_params"]
    WEIGHT = vision_params["WEIGHT_PATH"]
    
    export_model(WEIGHT)

if __name__ == "__main__":
    main()