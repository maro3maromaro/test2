import flet as ft
import json
import os
import datetime
import numpy as np
import base64
import io
from PIL import Image, ImageDraw, ImageFont
import glob
import traceback

# シミュレーション実行関数
def simu(params):
    """
    シミュレーションを実行し、結果を保存する
    
    Parameters:
    -----------
    params : dict
        シミュレーションパラメータ
    
    Returns:
    --------
    result : dict
        シミュレーション結果
    """
    # 結果を保存するディレクトリを作成
    date_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    data_dir = os.path.join("..", "data", date_str)
    input_dir = os.path.join(data_dir, "data", "input")
    output_dir = os.path.join(data_dir, "data", "output")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 入力パラメータをJSONとして保存
    with open(os.path.join(input_dir, "input.json"), "w") as f:
        json.dump(params, f, indent=4)
    
    # テスト用の出力データを生成
    beam_energy = float(params.get("beam_energy", 50))
    beam_current = float(params.get("beam_current", 10))
    beam_size = float(params.get("beam_size", 20))
    resist_thickness = float(params.get("resist_thickness", 300))
    pattern_width = float(params.get("pattern_width", 100))
    
    # テスト用のシミュレーション結果データ
    sim_result = {
        "exposure_time": beam_current * resist_thickness / (beam_energy * 1000),  # 単位: ms
        "development_depth": resist_thickness * 0.9,  # 単位: nm
        "pattern_width_actual": pattern_width * (1 + 0.05 * (beam_size / 20 - 1)),  # 単位: nm
        "beam_spot_profile": [beam_size * 0.5, beam_size, beam_size * 1.5]  # 単位: nm
    }
    
    # シミュレーション結果をJSONとして保存
    with open(os.path.join(output_dir, "output.json"), "w") as f:
        json.dump(sim_result, f, indent=4)
    
    # テスト用のCSVデータを生成（CDマップのプレビュー）
    cd_preview = []
    for i in range(5):
        row = []
        for j in range(5):
            dist = np.sqrt((i-2)**2 + (j-2)**2)
            cd_value = pattern_width * (1 - 0.1 * dist / 2.83) + np.random.normal(0, 3)
            row.append(cd_value)
        cd_preview.append(row)
    
    # CSVとして保存
    with open(os.path.join(output_dir, "cd_preview.csv"), "w") as f:
        for row in cd_preview:
            f.write(",".join([f"{val:.2f}" for val in row]) + "\n")
    
    # 最終結果
    result = {
        "date_dir": date_str,
        "params": params,
        "sim_result": sim_result
    }
    
    return result

# 解析実行関数
def Analyze(date_dir, params, ROI, X0, Y0, X_pitch, Y_pitch, X_num, Y_num):
    """
    解析を実行し、CD_map, pos_map, LER_mapを返す
    
    Returns:
    --------
    CD_map : np.ndarray
        臨界寸法マップ (20, 20)
    pos_map : np.ndarray
        位置ずれマップ (20, 20)
    LER_map : np.ndarray
        Line Edge Roughnessマップ (20, 20)
    """
    print(f"解析パラメータ: ROI={ROI}, X0={X0}, Y0={Y0}, X_pitch={X_pitch}, Y_pitch={Y_pitch}, X_num={X_num}, Y_num={Y_num}")
    
    # 常に20x20の配列を生成
    fixed_size = 20
    
    # テスト用データ生成
    # CDマップ - パターン幅をベースに変動を追加
    base_cd = float(params.get("pattern_width", 100))
    CD_map = np.zeros((fixed_size, fixed_size))
    
    # 位置ずれマップ
    pos_map = np.zeros((fixed_size, fixed_size))
    
    # LERマップ
    beam_size = float(params.get("beam_size", 20))
    LER_map = np.zeros((fixed_size, fixed_size))
    
    # データ生成
    for i in range(fixed_size):
        for j in range(fixed_size):
            # CDマップ
            dist_from_center = np.sqrt(((i - fixed_size/2)/(fixed_size/2))**2 + ((j - fixed_size/2)/(fixed_size/2))**2)
            cd_value = base_cd * (1 - 0.2 * dist_from_center) + np.random.normal(0, base_cd * 0.03)
            wave_pattern = 5.0 * np.sin(i/2) * np.cos(j/2)
            CD_map[i, j] = cd_value + wave_pattern
            
            # 位置ずれマップ
            x_dist = (i - fixed_size/2)/(fixed_size/2)
            y_dist = (j - fixed_size/2)/(fixed_size/2)
            pos_map[i, j] = 5.0 * np.sqrt(x_dist**2 + y_dist**2) + np.random.normal(0, 1.0)
            # 対角線パターン
            if (i + j) % 5 < 2:
                pos_map[i, j] += 2.0
            else:
                pos_map[i, j] -= 1.0
            
            # LERマップ
            gradient = j / fixed_size
            ler_value = (10.0 / beam_size) * (1 + 0.5 * gradient) + np.random.normal(0, 0.3)
            LER_map[i, j] = max(0.5, ler_value)
    
    print(f"マップサイズ: CD_map={CD_map.shape}, pos_map={pos_map.shape}, LER_map={LER_map.shape}")
    return CD_map, pos_map, LER_map

class PhotomaskApp:
    def __init__(self):
        self.app = ft.app(target=self.main)
        
    def main(self, page: ft.Page):
        self.page = page
        self.page.title = "フォトマスク電子ビーム描画シミュレーション・解析ツール"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        
        # アプリケーションの状態
        self.current_view = "input"  # 現在の画面
        self.simulation_result = None  # シミュレーション結果
        self.search_results = []  # 検索結果
        self.selected_result = None  # 選択された検索結果
        
        # パラメータの定義（15項目）
        self.param_fields = {
            "beam_energy": ft.TextField(label="ビームエネルギー [keV]", value="50"),
            "beam_current": ft.TextField(label="ビーム電流 [nA]", value="10"),
            "beam_size": ft.TextField(label="ビームサイズ [nm]", value="20"),
            "resist_thickness": ft.TextField(label="レジスト膜厚 [nm]", value="300"),
            "resist_sensitivity": ft.TextField(label="レジスト感度 [µC/cm²]", value="30"),
            "development_time": ft.TextField(label="現像時間 [sec]", value="60"),
            "development_temperature": ft.TextField(label="現像温度 [°C]", value="23"),
            "pattern_width": ft.TextField(label="パターン幅 [nm]", value="100"),
            "pattern_height": ft.TextField(label="パターン高さ [nm]", value="100"),
            "pattern_pitch_x": ft.TextField(label="パターンピッチX [nm]", value="200"),
            "pattern_pitch_y": ft.TextField(label="パターンピッチY [nm]", value="200"),
            "pattern_array_x": ft.TextField(label="パターン配列X", value="10"),
            "pattern_array_y": ft.TextField(label="パターン配列Y", value="10"),
            "substrate_material": ft.Dropdown(
                label="基板材料",
                options=[
                    ft.dropdown.Option("Si"),
                    ft.dropdown.Option("SiO2"),
                    ft.dropdown.Option("Cr"),
                ],
                value="Si"
            ),
            "resist_type": ft.Dropdown(
                label="レジストタイプ",
                options=[
                    ft.dropdown.Option("ポジティブ"),
                    ft.dropdown.Option("ネガティブ"),
                ],
                value="ポジティブ"
            ),
        }
        
        # 解析パラメータの定義
        self.analysis_fields = {
            "ROI": ft.TextField(label="ROI", value="center"),
            "X0": ft.TextField(label="X0 [nm]", value="0"),
            "Y0": ft.TextField(label="Y0 [nm]", value="0"),
            "X_pitch": ft.TextField(label="X_pitch [nm]", value="200"),
            "Y_pitch": ft.TextField(label="Y_pitch [nm]", value="200"),
            "X_num": ft.TextField(label="X_num", value="20"),
            "Y_num": ft.TextField(label="Y_num", value="20"),
        }
        
        # 初期画面の表示
        self.show_input_view()
        
    def show_input_view(self):
        """シミュレーションパラメータ入力画面を表示"""
        self.current_view = "input"
        
        # パラメータ入力フォームの作成
        param_rows = []
        for i in range(0, len(self.param_fields), 2):
            row_controls = []
            for j in range(2):
                if i + j < len(self.param_fields):
                    field_name = list(self.param_fields.keys())[i + j]
                    field = self.param_fields[field_name]
                    row_controls.append(ft.Container(field, expand=1, margin=5))
            param_rows.append(ft.Row(row_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            
        # ボタン
        btn_simulate = ft.ElevatedButton(
            text="シミュレーション実行",
            icon=ft.icons.PLAY_ARROW,
            on_click=self.run_simulation
        )
        
        btn_search = ft.ElevatedButton(
            text="過去の結果を検索",
            icon=ft.icons.SEARCH,
            on_click=self.search_results_handler
        )
        
        # レイアウト
        content = ft.Column(
            controls=[
                ft.Text("シミュレーションパラメータ入力", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                *param_rows,
                ft.Divider(),
                ft.Row(
                    [btn_simulate, btn_search],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                )
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        # 画面表示
        self.page.controls.clear()
        self.page.add(content)
        self.page.update()
        
    def run_simulation(self, e):
        """シミュレーションを実行する"""
        try:
            # パラメータの取得
            params = {}
            for name, field in self.param_fields.items():
                params[name] = field.value
                
            # シミュレーション実行
            self.page.splash = ft.ProgressBar()
            self.page.update()
            
            # シミュレーション実行（非同期にするべきだが、簡略化のため同期実行）
            self.simulation_result = simu(params)
            
            # 解析画面に移動
            self.page.splash = None
            self.show_analysis_view()
        except Exception as ex:
            print(f"シミュレーション実行エラー: {str(ex)}")
            error_details = traceback.format_exc()
            print(error_details)
            
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("エラー"),
                content=ft.Text(f"シミュレーション実行中にエラーが発生しました: {str(ex)}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.close_dialog())
                ]
            )
            self.page.dialog.open = True
            self.page.splash = None
            self.page.update()
        
    def search_results_handler(self, e):
        """過去の結果を検索"""
        try:
            self.search_results = []
            
            # 現在のパラメータを取得
            current_params = {}
            for name, field in self.param_fields.items():
                current_params[name] = field.value
                
            # 過去のデータを検索
            data_path = os.path.join("..", "data")
            if os.path.exists(data_path):
                date_dirs = glob.glob(os.path.join(data_path, "*"))
                
                for date_dir in date_dirs:
                    if os.path.isdir(date_dir):
                        input_json_path = os.path.join(date_dir, "data", "input", "input.json")
                        if os.path.exists(input_json_path):
                            try:
                                with open(input_json_path, "r") as f:
                                    params = json.load(f)
                                    
                                # パラメータが一致するか確認（簡易比較、実際には必要に応じて条件を調整）
                                match = True
                                for key, value in current_params.items():
                                    if key in params and str(params[key]) != str(value):
                                        match = False
                                        break
                                        
                                if match:
                                    date_name = os.path.basename(date_dir)
                                    self.search_results.append({
                                        "date_dir": date_name,
                                        "params": params
                                    })
                            except Exception as ex:
                                print(f"Error reading {input_json_path}: {str(ex)}")
            
            # 検索結果画面に移動
            self.show_search_results_view()
        except Exception as ex:
            print(f"検索エラー: {str(ex)}")
            error_details = traceback.format_exc()
            print(error_details)
            
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("エラー"),
                content=ft.Text(f"検索中にエラーが発生しました: {str(ex)}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.close_dialog())
                ]
            )
            self.page.dialog.open = True
            self.page.update()
        
    def show_search_results_view(self):
        """検索結果画面を表示"""
        self.current_view = "search_results"
        
        # 検索結果テーブルの作成
        table_columns = [
            ft.DataColumn(ft.Text("選択")),
            ft.DataColumn(ft.Text("日付")),
        ] + [
            ft.DataColumn(ft.Text(name)) for name in self.param_fields.keys()
        ]
        
        table_rows = []
        for i, result in enumerate(self.search_results):
            row_cells = [
                ft.DataCell(
                    ft.Checkbox(value=False, on_change=lambda e, idx=i: self.select_result(e, idx))
                ),
                ft.DataCell(ft.Text(result["date_dir"])),
            ]
            
            for name in self.param_fields.keys():
                value = result["params"].get(name, "")
                row_cells.append(ft.DataCell(ft.Text(str(value))))
                
            table_rows.append(ft.DataRow(cells=row_cells))
        
        results_table = ft.DataTable(
            columns=table_columns,
            rows=table_rows,
            border=ft.border.all(1, ft.colors.GREY_400),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_400),
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_400),
        )
        
        # ボタン
        btn_back = ft.ElevatedButton(
            text="シミュレーション条件入力に移る",
            icon=ft.icons.ARROW_BACK,
            on_click=lambda _: self.show_input_view()
        )
        
        btn_analyze = ft.ElevatedButton(
            text="解析モードに移る",
            icon=ft.icons.ANALYTICS,
            on_click=self.go_to_analysis_from_search
        )
        
        # レイアウト
        content = ft.Column(
            controls=[
                ft.Text("検索結果", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"検索結果: {len(self.search_results)}件"),
                ft.Divider(),
                ft.Container(
                    results_table,
                    height=400,
                    expand=True,
                    scroll=ft.ScrollMode.ALWAYS
                ),
                ft.Divider(),
                ft.Row(
                    [btn_back, btn_analyze],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                )
            ],
            spacing=10,
            expand=True
        )
        
        # 画面表示
        self.page.controls.clear()
        self.page.add(content)
        self.page.update()
        
    def select_result(self, e, idx):
        """検索結果を選択"""
        # チェックボックスの状態を更新
        for i, row in enumerate(self.page.controls[0].controls[3].content.rows):
            checkbox = row.cells[0].content
            if i == idx:
                checkbox.value = e.control.value
            else:
                checkbox.value = False
                
        # 選択された結果を保存
        if e.control.value:
            self.selected_result = self.search_results[idx]
        else:
            self.selected_result = None
            
        self.page.update()
        
    def go_to_analysis_from_search(self, e):
        """検索結果から解析画面に移動"""
        if self.selected_result:
            self.simulation_result = self.selected_result
            self.show_analysis_view()
        else:
            # 何も選択されていない場合はアラート表示
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("選択エラー"),
                content=ft.Text("解析する結果を選択してください。"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.close_dialog())
                ]
            )
            self.page.dialog.open = True
            self.page.update()
            
    def close_dialog(self):
        """ダイアログを閉じる"""
        self.page.dialog.open = False
        self.page.update()
            
    def show_analysis_view(self):
        """解析画面を表示"""
        self.current_view = "analysis"
        
        if not self.simulation_result:
            self.show_input_view()
            return
            
        # 現在のシミュレーション結果情報
        result_info = []
        result_info.append(ft.Text(f"日付: {self.simulation_result['date_dir']}", size=16))
        
        params_text = []
        for name, value in self.simulation_result["params"].items():
            label = self.param_fields[name].label if hasattr(self.param_fields[name], "label") else name
            params_text.append(f"{label}: {value}")
            
        result_info.append(
            ft.Container(
                ft.Column([ft.Text(text) for text in params_text]),
                padding=10,
                border=ft.border.all(1, ft.colors.GREY_400),
                border_radius=5,
                margin=ft.margin.only(bottom=10)
            )
        )
        
        # 解析パラメータ
        analysis_param_rows = []
        for i in range(0, len(self.analysis_fields), 3):
            row_controls = []
            for j in range(3):
                if i + j < len(self.analysis_fields):
                    field_name = list(self.analysis_fields.keys())[i + j]
                    field = self.analysis_fields[field_name]
                    row_controls.append(ft.Container(field, expand=1, margin=5))
            analysis_param_rows.append(ft.Row(row_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            
        # 解析実行ボタン
        btn_analyze = ft.ElevatedButton(
            text="解析実行",
            icon=ft.icons.ANALYTICS,
            on_click=self.run_analysis
        )
        
        btn_back = ft.ElevatedButton(
            text="シミュレーション条件入力に戻る",
            icon=ft.icons.ARROW_BACK,
            on_click=lambda _: self.show_input_view()
        )
        
        # ステータステキスト
        self.status_text = ft.Text("「解析実行」ボタンを押してください")
        
        # マップ表示用コンテナ
        self.cd_map_container = ft.Container(
            content=ft.Text("CDマップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=350,
            margin=10,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        self.pos_map_container = ft.Container(
            content=ft.Text("位置マップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=350,
            margin=10,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        self.ler_map_container = ft.Container(
            content=ft.Text("LERマップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=350,
            margin=10,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        # レイアウト
        content = ft.Column(
            controls=[
                ft.Text("解析モード", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                *result_info,
                ft.Divider(),
                ft.Text("解析パラメータ", size=16, weight=ft.FontWeight.BOLD),
                *analysis_param_rows,
                ft.Row(
                    [btn_analyze, btn_back],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                ),
                self.status_text,
                ft.Divider(),
                ft.Text("解析結果", size=16, weight=ft.FontWeight.BOLD),
                # 3つのマップを縦に並べて表示
                ft.Column([
                    ft.Text("CD Map", size=14, weight=ft.FontWeight.BOLD),
                    self.cd_map_container,
                    ft.Text("Position Map", size=14, weight=ft.FontWeight.BOLD),
                    self.pos_map_container,
                    ft.Text("LER Map", size=14, weight=ft.FontWeight.BOLD),
                    self.ler_map_container,
                ])
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        # 画面表示
        self.page.controls.clear()
        self.page.add(content)
        self.page.update()
        
    def run_analysis(self, e):
        """解析を実行する"""
        try:
            # パラメータの取得
            analysis_params = {}
            for name, field in self.analysis_fields.items():
                analysis_params[name] = field.value
                
            # 解析実行
            self.page.splash = ft.ProgressBar()
            self.status_text.value = "解析を実行中..."
            self.page.update()
            
            # 入力値の検証
            try:
                x_num = int(analysis_params["X_num"])
                y_num = int(analysis_params["Y_num"])
                if x_num <= 0 or y_num <= 0:
                    raise ValueError("X_numとY_numは正の整数である必要があります")
            except ValueError as ve:
                raise ValueError(f"パラメータエラー: {str(ve)}")
            
            # 常に20x20のマップを生成
            CD_map, pos_map, LER_map = Analyze(
                self.simulation_result["date_dir"],
                self.simulation_result["params"],
                analysis_params["ROI"],
                float(analysis_params["X0"]),
                float(analysis_params["Y0"]),
                float(analysis_params["X_pitch"]),
                float(analysis_params["Y_pitch"]),
                x_num,  # 実際には内部で20に上書きされる
                y_num   # 実際には内部で20に上書きされる
            )
            
            # マップを表示
            self.update_map_display(CD_map, pos_map, LER_map)
            
            # 成功メッセージ
            self.status_text.value = "解析が完了しました。マップを表示しています。"
            self.status_text.color = ft.colors.GREEN
            
        except Exception as ex:
            print(f"解析エラー: {str(ex)}")
            error_details = traceback.format_exc()
            print(error_details)
            
            self.status_text.value = f"解析中にエラーが発生しました: {str(ex)}"
            self.status_text.color = ft.colors.RED
            
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("解析エラー"),
                content=ft.Text(f"解析中にエラーが発生しました: {str(ex)}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.close_dialog())
                ]
            )
            self.page.dialog.open = True
            
        self.page.splash = None
        self.page.update()
        
    def update_map_display(self, CD_map, pos_map, LER_map):
        """マップ表示を更新"""
        try:
            print(f"マップサイズ: CD={CD_map.shape}, POS={pos_map.shape}, LER={LER_map.shape}")
            
            # CD Map
            print("CDマップの画像生成開始")
            cd_map_img = self.create_simple_heatmap(CD_map, "CD Map [nm]", "viridis")
            if cd_map_img:
                print("CDマップの画像をコンテナに設定")
                self.cd_map_container.content = ft.Image(src_base64=cd_map_img)
            else:
                self.cd_map_container.content = ft.Text("CDマップの生成に失敗しました", color=ft.colors.RED)
            
            # Position Map
            print("位置マップの画像生成開始")
            pos_map_img = self.create_simple_heatmap(pos_map, "Position Map [nm]", "coolwarm", center_zero=True)
            if pos_map_img:
                print("位置マップの画像をコンテナに設定")
                self.pos_map_container.content = ft.Image(src_base64=pos_map_img)
            else:
                self.pos_map_container.content = ft.Text("位置マップの生成に失敗しました", color=ft.colors.RED)
            
            # LER Map
            print("LERマップの画像生成開始")
            ler_map_img = self.create_simple_heatmap(LER_map, "LER Map [nm]", "hot")
            if ler_map_img:
                print("LERマップの画像をコンテナに設定")
                self.ler_map_container.content = ft.Image(src_base64=ler_map_img)
            else:
                self.ler_map_container.content = ft.Text("LERマップの生成に失敗しました", color=ft.colors.RED)
            
            # 画面更新
            print("画面更新")
            self.page.update()
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"マップ表示エラー: {str(e)}\n{error_details}")
            self.status_text.value = f"マップの表示中にエラーが発生しました: {str(e)}"
            self.status_text.color = ft.colors.RED
    
    def create_simple_heatmap(self, data, title, cmap_name, center_zero=False):
        """シンプルなヒートマップ生成関数"""
        try:
            # PILを使用してヒートマップを作成
            width, height = data.shape
            size_multiplier = 15  # 各セルのピクセルサイズ
            img_width = width * size_multiplier
            img_height = height * size_multiplier
            
            print(f"画像サイズ: {img_width}x{img_height}, データ形状: {data.shape}")
            
            # 値の正規化
            if center_zero:
                vmax = max(abs(np.min(data)), abs(np.max(data)))
                vmin = -vmax
            else:
                vmin = np.min(data)
                vmax = np.max(data)
            
            print(f"データ範囲: min={vmin}, max={vmax}")
            
            # カラーマップの定義
            if cmap_name == "viridis":
                colormap = [
                    (68, 1, 84),    # 暗い紫
                    (59, 82, 139),  # 青紫
                    (33, 145, 140), # ターコイズ
                    (94, 201, 98),  # 緑
                    (253, 231, 37)  # 黄色
                ]
            elif cmap_name == "coolwarm":
                colormap = [
                    (59, 76, 192),   # 暗い青
                    (124, 159, 249), # 明るい青
                    (247, 247, 247), # 白
                    (245, 117, 88),  # 明るい赤
                    (180, 4, 38)     # 暗い赤
                ]
            else:  # hot
                colormap = [
                    (0, 0, 0),       # 黒
                    (136, 0, 0),     # 暗い赤
                    (255, 0, 0),     # 赤
                    (255, 128, 0),   # オレンジ
                    (255, 255, 0),   # 黄色
                    (255, 255, 255)  # 白
                ]
            
            # 画像作成
            img = Image.new('RGB', (img_width, img_height), color='white')
            pixels = img.load()
            
            print("画像を作成しました")
            
            # 各セルごとに色を設定
            for i in range(width):
                for j in range(height):
                    value = data[i, j]
                    # 正規化
                    norm_value = (value - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                    norm_value = max(0, min(1, norm_value))  # 0～1の範囲に収める
                    
                    # カラーマップから色を取得
                    color = self.get_color_from_map(norm_value, colormap)
                    
                    # サイズに応じて拡大（各セルを複数ピクセルで表現）
                    for x in range(size_multiplier):
                        for y in range(size_multiplier):
                            # 座標計算
                            px = i * size_multiplier + x
                            py = j * size_multiplier + y
                            # 境界チェック
                            if 0 <= px < img_width and 0 <= py < img_height:
                                pixels[px, py] = color
            
            print("ピクセルを設定しました")
            
            # タイトルを追加
            title_height = 40
            img_with_title = Image.new('RGB', (img_width, img_height + title_height), color='white')
            img_with_title.paste(img, (0, title_height))
            draw = ImageDraw.Draw(img_with_title)
            
            # 利用可能なフォントを使用
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # タイトルとデータの統計情報を追加
            mean_val = np.mean(data)
            std_val = np.std(data)
            title_text = f"{title} (平均: {mean_val:.2f}, 標準偏差: {std_val:.2f})"
            draw.text((10, 10), title_text, fill=(0, 0, 0), font=font)
            
            # グリッド線を追加（オプション）
            self.add_grid_lines(img_with_title, width, height, size_multiplier, title_height)
            
            print("タイトルを追加しました")
            
            # 画像をBase64エンコード
            buffered = io.BytesIO()
            img_with_title.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            print("Base64エンコードしました")
            
            return img_base64
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"ヒートマップ生成エラー:\n{error_details}")
            return None
    
    def add_grid_lines(self, img, width, height, size_multiplier, offset_y):
        """ヒートマップにグリッド線を追加"""
        try:
            draw = ImageDraw.Draw(img)
            
            # 5間隔で太いグリッド線、それ以外は細い線
            for i in range(width + 1):
                line_color = (100, 100, 100) if i % 5 == 0 else (200, 200, 200)
                line_width = 2 if i % 5 == 0 else 1
                x = i * size_multiplier
                draw.line([(x, offset_y), (x, offset_y + height * size_multiplier)], fill=line_color, width=line_width)
            
            for j in range(height + 1):
                line_color = (100, 100, 100) if j % 5 == 0 else (200, 200, 200)
                line_width = 2 if j % 5 == 0 else 1
                y = j * size_multiplier + offset_y
                draw.line([(0, y), (width * size_multiplier, y)], fill=line_color, width=line_width)
        except Exception as e:
            print(f"グリッド線追加エラー: {str(e)}")
    
    def get_color_from_map(self, value, colormap):
        """0～1の値からカラーマップの色を取得"""
        if value <= 0:
            return colormap[0]
        if value >= 1:
            return colormap[-1]
        
        # 位置を計算
        position = value * (len(colormap) - 1)
        idx1 = int(position)
        idx2 = min(idx1 + 1, len(colormap) - 1)
        frac = position - idx1
        
        # 色の線形補間
        r = int(colormap[idx1][0] * (1 - frac) + colormap[idx2][0] * frac)
        g = int(colormap[idx1][1] * (1 - frac) + colormap[idx2][1] * frac)
        b = int(colormap[idx1][2] * (1 - frac) + colormap[idx2][2] * frac)
        
        return (r, g, b)

if __name__ == "__main__":
    app = PhotomaskApp()