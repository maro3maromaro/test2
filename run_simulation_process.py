# run_simulation_process.py
import sys
import json
import os
import traceback

def main():
    """
    コマンドライン引数からパラメータを読み取り、シミュレーションを実行し、結果を保存する
    引数1: 入力パラメータJSONファイルのパス
    引数2: 出力結果JSONファイルのパス
    """
    try:
        # 引数の取得
        if len(sys.argv) != 3:
            print("使用法: python run_simulation_process.py <入力パラメータファイル> <出力結果ファイル>")
            sys.exit(1)
            
        param_file = sys.argv[1]
        result_file = sys.argv[2]
        
        # パラメータの読み込み
        with open(param_file, 'r', encoding='utf-8') as f:
            simu_parameters = json.load(f)
        
        # ここで必要なインポートを行う（GUIプロセスと分離するため）
        from factories.SimulationFactory import SimulationFactory
        
        # シミュレーションオブジェクトの作成と実行
        simulation = SimulationFactory.cleate_simulation()
        result = simulation.run_simulation(simu_parameters)
        
        # 結果をJSONファイルに保存
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"シミュレーション完了、結果を {result_file} に保存しました")
        sys.exit(0)
        
    except Exception as e:
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        # エラー情報をファイルに保存
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2)
        except:
            # 最後の手段としてエラーファイルを作成
            with open(result_file + ".error", 'w', encoding='utf-8') as f:
                f.write(str(error_info))
                
        print(f"エラーが発生しました: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()