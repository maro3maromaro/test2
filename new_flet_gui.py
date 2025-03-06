import flet as ft
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUIを使わないバックエンドを設定
import matplotlib.pyplot as plt
import base64
import io
import json
import os
import datetime
import glob
import traceback
import multiprocessing as mp
import time

# 別プロセスで実行するシミュレーション関数
def run_simulation_in_process(params):
    """
    別プロセスでシミュレーションを実行する関数
    simulation.pyをここでインポートして実行する

    Parameters:
    -----------
    params : dict
        シミュレーションパラメータ

    Returns:
    --------
    dict
        シミュレーション結果
    """
    try:
        print("別プロセスでシミュレーション開始...")
        
        # simulation.pyをインポートする
        # 注意: この行は実際のsimulation.pyがある場合にコメントアウトを外す
        # import simulation
        
        # シミュレーション結果を保存するディレクトリを作成
        date_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        data_dir = os.path.join("..", "data", date_str)
        input_dir = os.path.join(data_dir, "data", "input")
        output_dir = os.path.join(data_dir, "data", "output")
        
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # 入力パラメータをJSONとして保存
        with open(os.path.join(input_dir, "input.json"), "w") as f:
            json.dump(params, f, indent=4)
            
        # 実際のシミュレーション呼び出し（コメントアウトを外す）
        # result = simulation.simulation(params)
        
        # テスト用のダミー結果（実際のシミュレーションの代わり）
        # 実際の実装では削除又はコメントアウトする
        print("シミュレーション実行中（テスト用ダミー処理）...")
        time.sleep(3)  # シミュレーション時間のシミュレーション
        
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
            
        result = {
            "date_dir": date_str,
            "params": params,
            "sim_result": sim_result
        }
        
        print("シミュレーション完了、結果を返します")
        return result
        
    except Exception as e:
        print(f"シミュレーション実行中のエラー: {str(e)}")
        traceback.print_exc()
        return {"error": str(e), "traceback": traceback.format_exc()}

# 解析実行関数
def Analyze(date_dir, params, ROI, X0, Y0, X_pitch, Y_pitch, X_num, Y_num):
    """
    解析を実行し、データフレームを返す
    
    Returns:
    --------
    CD_df : pd.DataFrame
        臨界寸法マップのデータフレーム
    pos_df : pd.DataFrame
        位置ずれマップのデータフレーム
    LER_df : pd.DataFrame
        Line Edge Roughnessマップのデータフレーム
    """
    print(f"解析パラメータ: ROI={ROI}, X0={X0}, Y0={Y0}, X_pitch={X_pitch}, Y_pitch={Y_pitch}, X_num={X_num}, Y_num={Y_num}")
    
    try:
        # CSVファイルが存在するかチェック
        csv_path = "CD_map.csv"
        if not os.path.exists(csv_path):
            # ファイルが見つからない場合はテストデータを生成
            print(f"警告: {csv_path} が見つかりません。テストデータを生成します。")
            # テスト用のデータフレーム生成
            fixed_size = 20
            
            # インデックスと列名を生成（実際の値を想定）
            y_indices = [f"Y{i}" for i in range(fixed_size)]
            # X軸は降順
            x_columns = [f"X{fixed_size - i - 1}" for i in range(fixed_size)]
            
            # CDマップのデータフレーム
            cd_data = np.zeros((fixed_size, fixed_size))
            base_cd = float(params.get("pattern_width", 100))
            
            for i in range(fixed_size):
                for j in range(fixed_size):
                    dist_from_center = np.sqrt(((i - fixed_size/2)/(fixed_size/2))**2 + ((j - fixed_size/2)/(fixed_size/2))**2)
                    cd_value = base_cd * (1 - 0.2 * dist_from_center) + np.random.normal(0, base_cd * 0.03)
                    wave_pattern = 5.0 * np.sin(i/2) * np.cos(j/2)
                    cd_data[i, j] = cd_value + wave_pattern
            
            CD_df = pd.DataFrame(data=cd_data, index=y_indices, columns=x_columns)
            
            # 位置ずれマップのデータフレーム
            pos_data = np.random.normal(0, 5, (fixed_size, fixed_size))
            pos_df = pd.DataFrame(data=pos_data, index=y_indices, columns=x_columns)
            
            # LERマップのデータフレーム
            ler_data = np.random.normal(3, 0.5, (fixed_size, fixed_size))
            LER_df = pd.DataFrame(data=ler_data, index=y_indices, columns=x_columns)
            
        else:
            # CSVファイルの読み込み
            print(f"CSVファイルを読み込み中: {csv_path}")
            CD_df = pd.read_csv(csv_path, index_col=0)
            print(f"読み込み完了: {CD_df.shape}")
            
            # テスト用の他のマップも生成（同じインデックスと列名を使用）
            pos_df = pd.DataFrame(
                data=np.random.normal(0, 5, CD_df.shape),
                index=CD_df.index,
                columns=CD_df.columns
            )
            
            LER_df = pd.DataFrame(
                data=np.random.normal(3, 0.5, CD_df.shape),
                index=CD_df.index,
                columns=CD_df.columns
            )
            
            # データの詳細を出力
            print(f"データの範囲: min={CD_df.values.min()}, max={CD_df.values.max()}")
            print(f"インデックス: {CD_df.index.tolist()}")
            print(f"列名: {CD_df.columns.tolist()}")
            
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {str(e)}")
        traceback.print_exc()
        # エラー時はテストデータを返す
        fixed_size = 20
        y_indices = [f"Y{i}" for i in range(fixed_size)]
        x_columns = [f"X{fixed_size - i - 1}" for i in range(fixed_size)]
        
        CD_df = pd.DataFrame(
            data=np.random.normal(100, 10, (fixed_size, fixed_size)),
            index=y_indices,
            columns=x_columns
        )
        
        pos_df = pd.DataFrame(
            data=np.random.normal(0, 5, (fixed_size, fixed_size)),
            index=y_indices,
            columns=x_columns
        )
        
        LER_df = pd.DataFrame(
            data=np.random.normal(3, 0.5, (fixed_size, fixed_size)),
            index=y_indices,
            columns=x_columns
        )
    
    return CD_df, pos_df, LER_df

class PhotomaskApp:
    def __init__(self):
        self.app = ft.app(target=self.main)
        
    def main(self, page: ft.Page):
        self.page = page
        self.page.title = "フォトマスク電子ビーム描画シミュレーション・解析ツール"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.window_width = 1280  # ウィンドウの初期幅を設定
        self.page.window_height = 900  # ウィンドウの初期高さを設定
        
        # アプリケーションの状態
        self.current_view = "input"  # 現在の画面
        self.simulation_result = None  # シミュレーション結果
        self.search_results = []  # 検索結果
        self.selected_result = None  # 選択された検索結果
        
        # プログレス表示用
        self.progress_bar = ft.ProgressBar()
        
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
        """シミュレーションを実行する - マルチプロセス版"""
        try:
            # パラメータの取得
            params = {}
            for name, field in self.param_fields.items():
                params[name] = field.value
                
            # プログレスバー表示 - 新しいoverlay APIを使用
            self.page.overlay.append(self.progress_bar)
            self.page.update()
            
            # マルチプロセスプールの作成
            ctx = mp.get_context('spawn')  # Windows互換性のため'spawn'を使用
            
            # 別プロセスでシミュレーション実行
            with ctx.Pool(processes=1) as pool:
                result = pool.apply(run_simulation_in_process, (params,))
                
                # エラーチェック
                if "error" in result:
                    raise Exception(f"シミュレーション実行中にエラーが発生しました: {result['error']}")
                
                self.simulation_result = result
            
            # プログレスバーを非表示
            self.page.overlay.clear()
            
            # 解析画面に移動
            self.show_analysis_view()
            
        except Exception as ex:
            print(f"シミュレーション実行エラー: {str(ex)}")
            traceback.print_exc()
            
            # プログレスバーを非表示
            self.page.overlay.clear()
            
            # エラーダイアログ表示
            self.page.dialog = ft.AlertDialog(
                title=ft.Text("エラー"),
                content=ft.Text(f"シミュレーション実行中にエラーが発生しました: {str(ex)}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda _: self.close_dialog())
                ]
            )
            self.page.dialog.open = True
            self.page.update()
        
    def search_results_handler(self, e):
        """過去の結果を検索"""
        try:
            self.search_results = []
            
            # 現在のパラメータを取得
            current_params = {}
            for name, field in self.param_fields.items():
                current_params[name] = field.value
                
            # プログレスバー表示
            self.page.overlay.append(self.progress_bar)
            self.page.update()
            
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
                                    
                                # パラメータが一致するか確認
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
            
            # プログレスバーを非表示
            self.page.overlay.clear()
            
            # 検索結果画面に移動
            self.show_search_results_view()
            
        except Exception as ex:
            print(f"検索エラー: {str(ex)}")
            traceback.print_exc()
            
            # プログレスバーを非表示
            self.page.overlay.clear()
            
            # エラーダイアログ
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
        
        # シミュレーションパラメータを横4列で表示
        param_grid = []
        params = self.simulation_result["params"]
        param_items = []
        
        # パラメータを4列のグリッドで表示するための準備
        for name, value in params.items():
            label = self.param_fields[name].label if hasattr(self.param_fields[name], "label") else name
            param_items.append((label, value))
        
        # 4列のグリッドとして表示
        for i in range(0, len(param_items), 4):
            row_controls = []
            for j in range(4):
                if i + j < len(param_items):
                    label, value = param_items[i + j]
                    row_controls.append(
                        ft.Container(
                            ft.Text(f"{label}: {value}", size=12),
                            width=280,  # 幅を固定
                            margin=5
                        )
                    )
            param_grid.append(ft.Row(row_controls))
        
        # パラメータグリッドをコンテナに配置
        result_info.append(
            ft.Container(
                ft.Column(param_grid),
                padding=10,
                border=ft.border.all(1, ft.colors.GREY_400),
                border_radius=5,
                margin=ft.margin.only(bottom=10)
            )
        )
        
        # 解析パラメータ
        analysis_param_rows = []
        for i in range(0, len(self.analysis_fields), 4):  # 横4列に変更
            row_controls = []
            for j in range(4):
                if i + j < len(self.analysis_fields):
                    field_name = list(self.analysis_fields.keys())[i + j]
                    field = self.analysis_fields[field_name]
                    row_controls.append(ft.Container(field, expand=1, margin=5))
            analysis_param_rows.append(ft.Row(row_controls, alignment=ft.MainAxisAlignment.START))
            
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
        
        # マップ表示用コンテナ - マップの高さを調整
        map_height = 320  # マップの高さを小さめに設定
        
        self.cd_map_container = ft.Container(
            content=ft.Text("CDマップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=map_height,
            margin=5,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        self.pos_map_container = ft.Container(
            content=ft.Text("位置マップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=map_height,
            margin=5,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        self.ler_map_container = ft.Container(
            content=ft.Text("LERマップはここに表示されます", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            height=map_height,
            margin=5,
            border=ft.border.all(1, ft.colors.GREY_400),
            border_radius=5
        )
        
        # マップのタイトルと表示を横に並べる
        map_row = ft.Row(
            [
                ft.Column([
                    ft.Text("CD Map", size=14, weight=ft.FontWeight.BOLD),
                    self.cd_map_container
                ], expand=1),
                ft.Column([
                    ft.Text("Position Map", size=14, weight=ft.FontWeight.BOLD),
                    self.pos_map_container
                ], expand=1),
                ft.Column([
                    ft.Text("LER Map", size=14, weight=ft.FontWeight.BOLD),
                    self.ler_map_container
                ], expand=1)
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=5
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
                # マップを横に並べて表示
                map_row
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
            self.page.overlay.append(self.progress_bar)
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
            
            # 解析実行 - データフレームとして返される
            CD_df, pos_df, LER_df = Analyze(
                self.simulation_result["date_dir"],
                self.simulation_result["params"],
                analysis_params["ROI"],
                float(analysis_params["X0"]),
                float(analysis_params["Y0"]),
                float(analysis_params["X_pitch"]),
                float(analysis_params["Y_pitch"]),
                x_num,
                y_num
            )
            
            # マップを表示
            self.update_map_display(CD_df, pos_df, LER_df)
            
            # 成功メッセージ
            self.status_text.value = "解析が完了しました。マップを表示しています。"
            self.status_text.color = ft.colors.GREEN
            
        except Exception as ex:
            print(f"解析エラー: {str(ex)}")
            traceback.print_exc()
            
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
            
        finally:
            # プログレスバーを非表示
            self.page.overlay.clear()
            self.page.update()
        
    def update_map_display(self, CD_df, pos_df, LER_df):
        """マップ表示を更新"""
        try:
            print(f"マップサイズ: CD={CD_df.shape}, POS={pos_df.shape}, LER={LER_df.shape}")
            
            # CD Map
            print("CDマップの画像生成開始")
            cd_map_img = self.create_matplotlib_heatmap(CD_df, "CD Map [nm]", "viridis")
            if cd_map_img:
                print("CDマップの画像をコンテナに設定")
                self.cd_map_container.content = ft.Image(src_base64=cd_map_img)
            else:
                self.cd_map_container.content = ft.Text("CDマップの生成に失敗しました", color=ft.colors.RED)
            
            # Position Map
            print("位置マップの画像生成開始")
            pos_map_img = self.create_matplotlib_heatmap(pos_df, "Position Map [nm]", "coolwarm", center_zero=True)
            if pos_map_img:
                print("位置マップの画像をコンテナに設定")
                self.pos_map_container.content = ft.Image(src_base64=pos_map_img)
            else:
                self.pos_map_container.content = ft.Text("位置マップの生成に失敗しました", color=ft.colors.RED)
            
            # LER Map
            print("LERマップの画像生成開始")
            ler_map_img = self.create_matplotlib_heatmap(LER_df, "LER Map [nm]", "hot")
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
    
    def create_matplotlib_heatmap(self, df, title, cmap_name, center_zero=False):
        """matplotlibを使用してデータフレームからヒートマップを生成する"""
        try:
            # Clean previous plot
            plt.clf()
            # 横に並べる場合はより小さいサイズで生成
            plt.figure(figsize=(6, 5))
            
            # データフレームから値の配列を取得
            data = df.values
            
            # 値の範囲を設定
            if center_zero:
                vmax = max(abs(np.min(data)), abs(np.max(data)))
                vmin = -vmax
            else:
                vmin = np.min(data)
                vmax = np.max(data)
            
            # ヒートマップを作成
            im = plt.imshow(data, cmap=cmap_name, interpolation='nearest', 
                           vmin=vmin, vmax=vmax, origin='upper', aspect='equal')
            
            # カラーバーを追加
            cbar = plt.colorbar(im)
            cbar.set_label(title)
            
            # タイトルを設定
            plt.title(title)
            
            # X軸とY軸のラベルを設定
            plt.xlabel("X軸")
            plt.ylabel("Y軸")
            
            # X軸とY軸の目盛りとラベルを設定
            # インデックスと列名のうち、5おきに表示する（表示を減らして見やすくする）
            xtick_step = max(1, len(df.columns) // 5)
            ytick_step = max(1, len(df.index) // 5)
            
            # X軸（列名）の目盛り - 5おきに表示
            xticks_pos = np.arange(0, len(df.columns), xtick_step)
            plt.xticks(xticks_pos, [df.columns[i] for i in xticks_pos], rotation=90)
            
            # Y軸（インデックス）の目盛り - 5おきに表示
            yticks_pos = np.arange(0, len(df.index), ytick_step)
            plt.yticks(yticks_pos, [df.index[i] for i in yticks_pos])
            
            # グリッド線の表示
            ax = plt.gca()
            ax.grid(True, color='white', linestyle='-', linewidth=0.5)
            ax.set_axisbelow(False)
            
            # 統計情報を表示
            mean_val = np.mean(data)
            std_val = np.std(data)
            min_val = np.min(data)
            max_val = np.max(data)
            
            stats_text = f"Mean: {mean_val:.2f}, Std: {std_val:.2f}\nMin: {min_val:.2f}, Max: {max_val:.2f}"
            plt.figtext(0.02, 0.02, stats_text, fontsize=8, bbox=dict(facecolor='white', alpha=0.8))
            
            # レイアウトの調整
            plt.tight_layout()
            
            # 画像をメモリに保存してBase64でエンコード
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Base64エンコード
            img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return img_base64
            
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Matplotlibヒートマップ生成エラー:\n{error_details}")
            return None

if __name__ == "__main__":
    app = PhotomaskApp()