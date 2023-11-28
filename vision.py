import os
from tkinter import Tk, filedialog
from google.cloud import vision_v1p3beta1 as vision
from tqdm import tqdm

# 키파일 경로 설정
keyfile_path = os.path.join(os.path.dirname(__file__), "theta-signal-405105-9d9fba79afa4.json")

# Names of likelihood from google.cloud.vision.enums
likelihood_name = (
    "UNKNOWN",
    "VERY_UNLIKELY",
    "UNLIKELY",
    "POSSIBLE",
    "LIKELY",
    "VERY_LIKELY",
)

def display_precheck_info():
    print("이미지를 검사하기 전에 다음과 같은 정보를 제공합니다:")
    print("성인성: 성인용 콘텐츠에는 과도한 노출, 포르노 이미지나 만화, 성행위 등의 요소가 포함될 수 있습니다.")
    print("조작성: 재미있거나 불쾌하게 보이도록 이미지의 표준 버전을 수정했을 가능성입니다.")
    print("폭력성: 폭력적인 콘텐츠 가능성이 높습니다.")
    print("선정성: 외설적인 콘텐츠 가능성이 있습니다.")

def determine_game_rating(safe_search_result):
    # 등급 기준에 따라 각 요소에 점수를 할당합니다.
    adult_score = likelihood_name[safe_search_result.adult]
    violence_score = likelihood_name[safe_search_result.violence]
    racy_score = likelihood_name[safe_search_result.racy]

    # 각 등급에 따라 부여 기준을 설정합니다.
    def determine_level(score):
        if score in ["VERY_UNLIKELY", "UNLIKELY"]:
            return "낮음"
        elif score == "POSSIBLE":
            return "중간"
        elif score == "LIKELY":
            return "높음"
        elif score == "VERY_LIKELY":
            return "매우높음"
        else:
            return "알 수 없음"

    adult_level = determine_level(adult_score)
    violence_level = determine_level(violence_score)
    racy_level = determine_level(racy_score)

    # 각 등급에 대한 결과를 출력하지 않고 등급만 반환합니다.
    if "VERY_LIKELY" in [adult_score, violence_score, racy_score]:
        return "청소년이용불가", adult_level, violence_level, racy_level
    elif "LIKELY" in [adult_score, violence_score, racy_score]:
        return "15세 이용가", adult_level, violence_level, racy_level
    elif "POSSIBLE" in [adult_score, violence_score, racy_score]:
        return "12세 이용가", adult_level, violence_level, racy_level
    else:
        return "전체이용가", adult_level, violence_level, racy_level

def detect_safe_search(path):
    """Detects unsafe features in the file."""
    try:
        # 환경 변수를 통해 키파일 경로 설정
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile_path
        client = vision.ImageAnnotatorClient()

        with open(path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        response = client.safe_search_detection(image=image)
        safe = response.safe_search_annotation

        # 게임 등급 출력
        game_rating, adult_level, violence_level, racy_level = determine_game_rating(safe)
        
        return game_rating, adult_level, violence_level, racy_level
        
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return None, None, None, None

def select_folder_and_scan():
    root = Tk()
    root.withdraw()

    display_precheck_info()

    folder_path = filedialog.askdirectory(title="폴더 선택")
    root.destroy()

    if folder_path:
        files_to_scan = [
            os.path.join(folder_path, filename)
            for filename in os.listdir(folder_path)
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp"))
        ]

        # 각 이미지에 대한 등급 및 세부 정보를 저장할 리스트
        results = []

        for file_path in tqdm(files_to_scan, desc="진행률", unit="파일"):
            game_rating, adult_level, violence_level, racy_level = detect_safe_search(file_path)
            if game_rating:
                # 각 이미지의 결과를 리스트에 추가
                results.append((file_path, game_rating, adult_level, violence_level, racy_level))

        # 대표 등급 결정
        representative_rating = determine_representative_rating([result[1] for result in results])

        # 각 이미지에 대한 결과와 대표 등급 출력
        for result in results:
            file_path, game_rating, adult_level, violence_level, racy_level = result
            print(f"{file_path}에 대한 결과:")
            print(f"성인성: {adult_level}")
            print(f"조작성: {violence_level}")
            print(f"폭력성: {racy_level}")
            print(f"선정성: {racy_level}")

        # 대표 등급 출력
        print(f"{', '.join([f'{os.path.basename(result[0])} {result[1]}' for result in results])} ")
        print(f"\n게임 등급: {representative_rating}")


    else:
        print("폴더가 선택되지 않았습니다. 종료합니다.")

def determine_representative_rating(ratings):
    if "청소년이용불가" in ratings:
        return "청소년이용불가"
    elif "15세 이용가" in ratings:
        return "15세 이용가"
    elif "12세 이용가" in ratings:
        return "12세 이용가"
    else:
        return "전체이용가"

if __name__ == "__main__":
    select_folder_and_scan()

    # 사용자 입력을 기다리며 메시지를 출력
    input("프로그램을 종료하려면 엔터 키를 누르세요.")
