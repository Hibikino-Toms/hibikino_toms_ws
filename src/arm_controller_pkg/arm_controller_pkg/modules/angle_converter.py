class AngleConverter():
    def __init__(self, dxl_params):
        self.LIMIT_DXL1 = (dxl_params["DXL_1_MIN_DEG"], dxl_params["DXL_1_MAX_DEG"])
        self.LIMIT_DXL3 = (dxl_params["DXL_3_MIN_DEG"], dxl_params["DXL_3_MAX_DEG"])
        self.LIMIT_DXL5 = (dxl_params["DXL_5_MIN_DEG"], dxl_params["DXL_5_MAX_DEG"])
        
    # アーム座標系の角度からモーターの角度系に変換する関数
    def ik_ang2dxl_ang(self, ik_angles_list):
        angles_lists_motor = []
        angles_lists_motor = [ik_angles_list[0] + 90, ik_angles_list[1] + 90, ik_angles_list[2] + 180]

        # 制限範囲内かのチェック
        check = (
            self.LIMIT_DXL1[0] <= angles_lists_motor[0] <= self.LIMIT_DXL1[1] and
            self.LIMIT_DXL3[0] <= angles_lists_motor[1] <= self.LIMIT_DXL3[1] and
            self.LIMIT_DXL5[0] <= angles_lists_motor[2] <= self.LIMIT_DXL5[1]
        )
        
        return angles_lists_motor, check

    # モータの角度系から逆運動学の角度系に変換する関数
    def dxl_ang2ik_ang(self, motor_angles_list):
        angles_lists_ik = []
        angles_lists_ik = [motor_angles_list[0] - 90, motor_angles_list[1] - 90, motor_angles_list[2] - 180]
        
        return angles_lists_ik