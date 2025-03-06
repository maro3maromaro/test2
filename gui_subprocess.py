# gui.py内の関連コードを修正

import subprocess
import sys
import os
import json
import tempfile
import threading

class GUIApplication:
    # ... 既存のコード ...
    
    def run_simulation(self, e):
        """シミュレーションを別プロセスで実行する"""
        try:
            # パラメータの取得
            params = {}
            for name, field in self.param_fields.items():
                params[name] = field.value
                
            # プログレスバー表示
            self.page.overlay.append(self.progress_bar)
            self.page.update()
            
            # 別スレッドでシミュレーションを実行
            threading.Thread(
                target=self._execute_simulation_process,
                args=(params,),
                daemon=True
            ).start()
            
        except Exception as ex:
            print(f"シミュレーション実行エラー: {str(ex)}")
            traceback.print_exc()
            
            # プログレスバーを非表示
            self.page.overlay.clear()
            
            # エラーダイアログ表示
            self._show_error_dialog(f"シミュレーション実行準備中にエラーが発生: {str(ex)}")
    
    def _execute_simulation_process(self, params):
        """別プロセスでシミュレーションを実行（スレッド内から呼ばれる）"""
        try:
            # 一時ファイルの作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                param_file = f.name
                json.dump(params, f)
            
            # 結果用の一時ファイル
            result_file = tempfile.mktemp(suffix='.json')
            
            # シミュレーション実行コマンド
            cmd = [
                sys.executable, 
                "run_simulation_process.py",
                param_file,
                result_file
            ]
            
            # サブプロセス実行（タイムアウト付き）
            timeout_seconds = 3600  # 1時間
            try:
                # 標準出力とエラー出力をキャプチャ
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                
                # 通信をモニタリング
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                
                if process.returncode != 0:
                    raise Exception(f"プロセスがエラーコード {process.returncode} で終了\n{stderr}")
                
                # 結果を読み込み
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                
                # エラーチェック
                if isinstance(result_data, dict) and "error" in result_data:
                    raise Exception(f"シミュレーションエラー: {result_data['error']}\n{result_data.get('traceback', '')}")
                
                # 結果を保存
                self.simulation_result = result_data
                
                # UI更新（メインスレッドで実行）
                self.page.add_event(lambda _: self._simulation_completed())
                
            except subprocess.TimeoutExpired:
                # タイムアウト時はプロセスを強制終了
                process.kill()
                raise Exception(f"シミュレーションが {timeout_seconds} 秒を超えて応答しないため中断しました")
                
        except Exception as ex:
            print(f"シミュレーション実行中のエラー: {str(ex)}")
            traceback.print_exc()
            # メインスレッドでエラー表示
            self.page.add_event(lambda _: self._simulation_failed(ex))
            
        finally:
            # 一時ファイルの削除
            try:
                if os.path.exists(param_file):
                    os.unlink(param_file)
                if os.path.exists(result_file):
                    os.unlink(result_file)
            except:
                pass
    
    def _simulation_completed(self):
        """シミュレーション完了時の処理（メインスレッドで実行）"""
        # プログレスバーを非表示
        self.page.overlay.clear()
        
        # 解析画面に移動
        self.show_analysis_view()
    
    def _simulation_failed(self, ex):
        """シミュレーション失敗時の処理（メインスレッドで実行）"""
        # プログレスバーを非表示
        self.page.overlay.clear()
        
        # エラーダイアログ表示
        self._show_error_dialog(f"シミュレーション実行中にエラーが発生: {str(ex)}")
    
    def _show_error_dialog(self, message):
        """エラーダイアログを表示"""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("エラー"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda _: self.close_dialog())
            ]
        )
        self.page.dialog.open = True
        self.page.update()