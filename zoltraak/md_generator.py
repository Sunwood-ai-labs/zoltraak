import os
import pyperclip
import anthropic
from dotenv import load_dotenv
from groq import Groq  # Groqをインポート
from tqdm import tqdm  # tqdmをインポート
import threading
import time
import sys

load_dotenv()  # .envファイルから環境変数を読み込む
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")  # 環境変数からAnthropicのAPI keyを取得
groq_api_key = os.getenv("GROQ_API_KEY")  # 環境変数からGroqのAPI keyを取得


def generate_md_from_prompt(
    goal_prompt,
    target_file_path,
    developer="anthropic",  # デベロッパーを指定する引数を追加
    model_name="claude-3-opus-20240229",  # モデル名の引数を独立させる
    compiler_path=None,
    formatter_path=None,
    open_file=True,  # ファイルを開くかどうかのフラグを追加
):
    # プロンプトコンパイラとプロンプトフォーマッタを変数として受け取る
    prompt_compiler = os.path.basename(compiler_path) if "grimoires" in compiler_path else compiler_path
    prompt_formatter = os.path.basename(formatter_path) if "grimoires" in formatter_path else formatter_path
    
    print(f"""
==============================================================
目標                         : {goal_prompt}
要件定義書                   : {target_file_path}
プロンプトコンパイラ (起動式): {prompt_compiler}
プロンプトフォーマッタ       : {prompt_formatter}
LLMベンダー                  : {developer}
モデル名                     : {model_name}
ファイルを開く               : {open_file}
==============================================================
    """)


    """
    promptから要件定義書（マークダウンファイル）を生成する関数

    Args:
        goal_prompt (str): 要件定義書の生成に使用するプロンプト
        target_file_path (str): 生成する要件定義書のパス
        developer (str): 使用するデベロッパー（デフォルトは "anthropic"）
        model_name (str): 使用するモデルの名前（デフォルトは "claude-3-opus-20240229"）
        compiler_path (str): コンパイラのパス（デフォルトはNone）
        formatter_path (str): フォーマッタのパス（デフォルトはNone）
        open_file (bool): ファイルを開くかどうかのフラグ（デフォルトはTrue）
    """
    prompt = create_prompt(goal_prompt, compiler_path, formatter_path)        # プロンプトを作成
    # print("goal_prompt", goal_prompt)
    # print("promtp", prompt)
    
    done = False  # スピナーの終了フラグを追加
    spinner_thread = threading.Thread(target=show_spinner, args=(lambda: done, "要件定義書執筆"))  # スピナーを表示するスレッドを作成し、終了フラグとgoalを渡す
    spinner_thread.start()  # スピナーの表示を開始
    
    response = generate_response(                                             # developerごとの分岐を関数化して応答を生成
        developer, model_name, prompt                                         # - デベロッパー、モデル名、プロンプトを引数に渡す
    )                                                                         #
    
    done = True  # 応答生成後にスピナーの終了フラグをTrueに設定
    spinner_thread.join()  # スピナーの表示を終了
    
    md_content = response.strip()                                             # 生成された要件定義書の内容を取得し、前後の空白を削除
    save_md_content(md_content, target_file_path)                             # 生成された要件定義書の内容をファイルに保存
    print_generation_result(target_file_path, open_file)                      # 生成結果を出力し、open_fileフラグに応じてファイルを開く


def show_spinner(done, goal):
    """スピナーを表示する関数

    Args:
        done (function): スピナーを終了するかどうかを判定する関数
    """
    progress_bar = "━" * 22

    spinner_base = goal + "中... 🪄 "
    spinner_animation = [
        f"{progress_bar[:i]}☆ﾟ.*･｡ﾟ{' ' * (len(progress_bar) - i)}"
        for i in range(1, len(progress_bar) + 1)
    ] + [f"{progress_bar}☆ﾟ.*･｡"]
    spinner = [spinner_base + anim for anim in spinner_animation]
    
     # リッチなスピナーのアニメーションパターンを定義。各フレームの末尾に「...」を追加して改行
    while not done():                                                   # done()がFalseの間、スピナーを表示し続ける
        for cursor in spinner:                                          # - スピナーのアニメーションパターンを順番に処理
            sys.stdout.write(cursor + "\b" * (len(cursor)+10))               # -- カーソル文字を出力し、その文字数分だけバックスペースを出力して上書き
            sys.stdout.flush()                                          # -- 出力をフラッシュして即時表示
            time.sleep(0.1)                                             # -- 0.1秒のディレイを追加



def generate_response(developer, model_name, prompt):
    """
    対応デベロッパーごとに分岐してレスポンスを生成する関数

    現在対応しているデベロッパーとモデルは以下の通りです:
    - Anthropic: 
      - claude-3-opus-20240229
      - claude-3-sonnet-20240229
      - claude-3-haiku-20240307
    - Groq:
      - llama3-8b-8192
      - llama3-70b-8192
      - llama2-70b-4096
      - mixtral-8x7b-32768
      - gemma-7b-it

    Args:
        developer (str): 使用するデベロッパー名（"anthropic" または "groq"）
        model_name (str): 使用するモデルの名前
        prompt (str): APIに送信するプロンプト

    Returns:
        str: APIから生成されたレスポンス
    """
    if developer == "groq":  # Groqを使用する場合
        response = create_prompt_and_get_response_groq(model_name, prompt)
    elif developer == "anthropic":  # Anthropicを使用する場合
        response = create_prompt_and_get_response_anthropic(model_name, prompt, 4000, 0.7)
    
    else:  # 想定外のデベロッパーの場合
        raise ValueError(
            f"サポートされていないデベロッパー: {developer}。"
            "サポートされているデベロッパーは 'anthropic' と 'groq' です。"
        )
    return response

def create_prompt_and_get_response_anthropic(model, prompt, max_tokens, temperature):
    """
    Anthropic APIを使用して、指定されたモデルでプロンプトに基づいてテキストを生成する関数

    Args:
        model (str): 使用するモデルの名前
        prompt (str): 送信するプロンプト
        max_tokens (int): 生成する最大トークン数
        temperature (float): 生成の多様性を制御する温度パラメータ

    Returns:
        str: 生成されたテキスト
    """
    client = anthropic.Anthropic(api_key=anthropic_api_key)  # Anthropic APIクライアントを作成
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system="",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def create_prompt_and_get_response_groq(model, prompt):
    """
    Groq APIを使用して、指定されたモデルでプロンプトに基づいてテキストを生成する関数

    Args:
        model (str): 使用するモデルの名前
        prompt (str): 送信するプロンプト

    Returns:
        str: 生成されたテキスト
    """
    client = Groq(api_key=groq_api_key)  # Groq APIクライアントを作成
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
    )
    return chat_completion.choices[0].message.content.strip()

def create_prompt(goal_prompt, compiler_path="grimoires/compiler/dev_obj.md", formatter_path=None):
    """
    LLMへのプロンプトを作成する関数

    Args:
        goal_prompt (str): 要件定義書の生成に使用するプロンプト
        compiler_path (str): コンパイラのパス
        formatter_path (str): フォーマッタのパス

    Returns:
        str: 作成されたプロンプト
    """
    # prompt_file = "grimoires/compiler/dev_obj.md"  # デフォルトのプロンプトファイルのパスを指定
    # if compiler_path:  # コンパイラパスが指定されている場合
        # prompt_file = compiler_path  # - プロンプトファイルのパスをコンパイラパスに変更

    formatter = get_formatter(formatter_path)

    if os.path.exists(compiler_path):  # プロンプトファイルが存在する場合
        with open(compiler_path, "r") as file:  # - プロンプトファイルを読み込みモードで開く
            prompt = file.read().format(
                prompt=goal_prompt
            )  # -- プロンプトファイルの内容を読み込み、goal_promptを埋め込む
        prompt = prompt + formatter  # - プロンプトにフォーマッタを追加
    else:  # プロンプトファイルが存在しない場合
        print(f"プロンプトファイル {compiler_path} が見つかりません。")  # - エラーメッセージを表示
        prompt = ""

    return prompt


def get_formatter(formatter_path):
    """
    フォーマッタを取得する関数

    Args:
        formatter_path (str): フォーマッタのパス

    Returns:
        str: フォーマッタの内容
    """
    if formatter_path is None:  # フォーマッタパスが指定されていない場合
        formatter = ""  # - フォーマッタを空文字列に設定
    else:  # フォーマッタパスが指定されている場合
        if os.path.exists(formatter_path):  # -- フォーマッタファイルが存在する場合
            with open(formatter_path, "r") as file:  # --- フォーマッタファイルを読み込みモードで開く
                formatter = file.read()  # ---- フォーマッタの内容を読み込む
        else:  # -- フォーマッタファイルが存在しない場合
            print(f"フォーマッタファイル {formatter_path} が見つかりません。")  # --- エラーメッセージを表示
            formatter = ""  # --- フォーマッタを空文字列に設定

    return formatter


def save_md_content(md_content, target_file_path):
    """
    生成された要件定義書の内容をファイルに保存する関数

    Args:
        md_content (str): 生成された要件定義書の内容
        target_file_path (str): 保存先のファイルパス
    """
    requirements_dir = "requirements"                                         # 生成された要件定義書をrequirements/の中に格納する
    os.makedirs(requirements_dir, exist_ok=True)                              # - requirements/ディレクトリを作成（既に存在する場合は何もしない）
    target_file_name = os.path.basename(target_file_path)                     # - ターゲットファイルのファイル名を取得
    target_file_path = os.path.join(requirements_dir, target_file_name)       # - requirements/ディレクトリとファイル名を結合してターゲットファイルのパスを生成
    with open(target_file_path, "w") as target_file:                          # ターゲットファイルを書き込みモードで開く
        target_file.write(md_content)                                         # - 生成された要件定義書の内容をファイルに書き込む

def print_generation_result(target_file_path, open_file=True):
    """
    要件定義書の生成結果を表示する関数

    Args:
        target_file_path (str): 生成された要件定義書のファイルパス
        open_file (bool): ファイルを開くかどうかのフラグ（デフォルトはTrue）
    """
    req = "requirements"
    target_file_path = f"{req}/{target_file_path}"
    print(f"\033[32m要件定義書を生成しました: {target_file_path}\033[0m")  # 要件定義書の生成完了メッセージを緑色で表示
    
    # ユーザーに要件定義書からディレクトリを構築するかどうかを尋ねる
    build_directory = input("要件定義書からディレクトリを構築しますか？ (y/n): ")
    
    if build_directory.lower() == 'y':
        # ユーザーがyと答えた場合、zoltraakコマンドを実行してディレクトリを構築
        import subprocess
        subprocess.run(["zoltraak", target_file_path])
    else:
        # ユーザーがnと答えた場合、既存の手順を表示
        print(f"\033[33m以下のコマンドをコピーして、ターミナルに貼り付けて実行してください。\033[0m")  # 実行方法の説明を黄色で表示
        print(f"\033[36mzoltraak {target_file_path}\033[0m")  # 実行コマンドを水色で表示
        pyperclip.copy(f"zoltraak {target_file_path}")  # 実行コマンドをクリップボードにコピー
        print("\033[35mコマンドをクリップボードにコピーしました。ターミナルに貼り付けて実行できます。\033[0m")  # コピー完了メッセージを紫色で表示
        