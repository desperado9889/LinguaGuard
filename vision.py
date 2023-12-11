import os
from tkinter import Tk, filedialog, Label, Button, Listbox, Scrollbar, StringVar, Entry, Frame
from tkinter.ttk import Progressbar
from tkinter import PhotoImage, messagebox
from google.cloud import vision_v1p3beta1 as vision
from tqdm import tqdm
import sys

# 키파일 경로 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'theta-signal-405105-e800f4a344b4.json'

# Names of likelihood from google.cloud.vision.enums
likelihood_name = (
    "UNKNOWN",
    "VERY_UNLIKELY",
    "UNLIKELY",
    "POSSIBLE",
    "LIKELY",
    "VERY_LIKELY",
)

class ImageScannerGUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("이미지 스캐너")

        # 이미지 폴더 레이블 및 버튼 프레임
        folder_frame = Frame(self.root)
        folder_frame.pack()

        self.folder_path_label = Label(folder_frame, text="이미지 폴더:")
        self.folder_path_label.pack(side="left")

        self.folder_path_var = StringVar()
        self.folder_path_entry = Entry(folder_frame, textvariable=self.folder_path_var, state="disabled", width=50)
        self.folder_path_entry.pack(side="left")

        self.browse_button = Button(folder_frame, text="폴더 선택", command=self.browse_folder)
        self.browse_button.pack(side="left")

        # 스캔 시작 버튼
        self.scan_button = Button(self.root, text="스캔 시작", command=self.select_folder_and_scan)
        self.scan_button.pack()

        # 결과를 표시할 Listbox 및 Scrollbar
        self.results_listbox = Listbox(self.root, width=50, height=10)
        self.results_listbox.pack()

        self.scrollbar = Scrollbar(self.root, orient="vertical")
        self.scrollbar.config(command=self.results_listbox.yview)
        self.scrollbar.pack(side="right", fill="y")

        # 진행률 및 프로그레스 바 초기화
        self.progress_label = Label(self.root, text="")
        self.progress_label.pack()
        self.progress_bar = Progressbar(self.root, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack()

        # Vision API 클라이언트 초기화
        self.vision_client = vision.ImageAnnotatorClient()

        self.root.mainloop()

    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="폴더 선택")
        self.folder_path_var.set(folder_path)

    def determine_representative_rating(self, ratings):
        if "청소년이용불가" in ratings:
            return "청소년이용불가", "GRAC_18.png"
        elif "15세 이용가" in ratings:
            return "15세 이용가", "GRAC_15.png"
        elif "12세 이용가" in ratings:
            return "12세 이용가", "GRAC_12.png"
        else:
            return "전체이용가", "GRAC_ALL.png"

    def determine_game_rating(self, safe_search_result):
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

    def detect_safe_search(self, path):
        """Detects unsafe features in the file."""
        try:
            with open(path, "rb") as image_file:
                content = image_file.read()

            image = vision.Image(content=content)

            response = self.vision_client.safe_search_detection(image=image)
            safe = response.safe_search_annotation

            # 게임 등급 출력
            game_rating, _, _, _ = self.determine_game_rating(safe)

            return game_rating

        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
            return None

    def select_folder_and_scan(self):
        folder_path = self.folder_path_var.get()
        if folder_path:
            files_to_scan = [
                os.path.join(folder_path, filename)
                for filename in os.listdir(folder_path)
                if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp"))
            ]

            # 각 이미지에 대한 등급 및 세부 정보를 저장할 리스트
            results = []

            # 파일 스캔 진행률을 표시하기 위한 변수
            total_files = len(files_to_scan)
            for i, file_path in enumerate(tqdm(files_to_scan, desc="진행률", unit="파일", file=sys.stdout, dynamic_ncols=True)):
                game_rating = self.detect_safe_search(file_path)
                if game_rating:
                    # 각 이미지의 결과를 리스트에 추가
                    results.append((file_path, game_rating))

                # 진행률 업데이트
                progress_value = (i + 1) / total_files * 100
                self.progress_bar["value"] = progress_value
                self.root.update_idletasks()

            # 대표 등급 결정
            representative_rating, representative_image = self.determine_representative_rating([result[1] for result in results])

            # 결과 및 대표 등급 출력
            for result in results:
                file_path, game_rating = result
                result_text = f"{file_path}에 대한 결과:\n게임 등급: {game_rating}\n"
                self.results_listbox.insert("end", result_text)

            # 대표 등급 및 이미지 출력
            result_text = f"\n대표 등급: {representative_rating}"
            self.results_listbox.insert("end", result_text)

            # 대표 등급 이미지 표시
            img_path = os.path.join(os.path.dirname(__file__), representative_image)
            img = PhotoImage(file=img_path)
            img = img.subsample(4)  # 이미지 크기 조절 (예: 2배 축소)
            label = Label(self.root, image=img)
            label.image = img  # 참조를 유지하기 위해
            label.pack()


            # 진행률 라벨 업데이트
            self.progress_label.config(text="스캔 완료")

        else:
            messagebox.showwarning("경고", "폴더가 선택되지 않았습니다. 종료합니다.")

if __name__ == "__main__":
    ImageScannerGUI()
