import tkinter as tk
from tkinter import ttk, messagebox
import pyproj
import math
import argparse
import sys
import webbrowser

# --- 計算 UTM Zone ---
def get_utm_zone(longitude):
    return math.floor((longitude + 180) / 6) + 1

# --- 經緯度轉平面座標（根據不同 datum 判斷投影方式） ---
def latlon_to_projected(lat, lon, datum_key):
    try:
        if not (-90 <= lat <= 90):
            raise ValueError("緯度必須在 -90 到 90 度之間")
        if not (-180 <= lon <= 180):
            raise ValueError("經度必須在 -180 到 180 度之間")

        datum_epsg = DATUMS[datum_key]
        source_crs = pyproj.CRS(datum_epsg)

        if datum_key == 'TWD97':
            # 使用 TWD97 TM2 中央經線 121 度（EPSG:3826）
            target_crs = pyproj.CRS("EPSG:3826")
            zone = "TM2-121"
            is_south = False
        else:
            zone = get_utm_zone(lon)
            is_south = lat < 0
            utm_epsg = 32700 + zone if is_south else 32600 + zone
            target_crs = pyproj.CRS.from_epsg(utm_epsg)

        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

        return x, y, zone, is_south

    except Exception as e:
        print(f"轉換錯誤: {e}")
        return None, None, None, None


# --- 平面座標轉經緯度 ---
def projected_to_latlon(x, y, zone, is_south, datum_key):
    """
    將平面座標轉換回經緯度。

    Args:
        x (float): Easting 座標值。
        y (float): Northing 座標值。
        zone (int): UTM Zone (對於 WGS 84)。對於 TWD97，此參數會被忽略。
        is_south (bool): 是否為南半球 (對於 WGS 84)。對於 TWD97，此參數會被忽略。
        datum_key (str): 大地基準的鍵名 ('WGS 84' 或 'TWD97')。

    Returns:
        tuple: (longitude, latitude) 或 (None, None) 如果轉換失敗。
    """
    try:
        datum_epsg = DATUMS[datum_key]
        target_crs = pyproj.CRS(datum_epsg) # 目標是經緯度

        if datum_key == 'TWD97':
            # 來源是 TWD97 TM2 (EPSG:3826)
            source_crs = pyproj.CRS("EPSG:3826")
            # TWD97 轉換不需要 zone 和 is_south，但保留參數以保持介面一致性
            print("執行 TWD97 平面座標 -> 經緯度 轉換 (EPSG:3826 -> EPSG:3824)")
        elif datum_key == 'WGS 84':
            if not isinstance(zone, int) or not (1 <= zone <= 60):
                 raise ValueError("UTM Zone 必須是 1 到 60 之間的整數")
            utm_epsg = 32700 + zone if is_south else 32600 + zone
            source_crs = pyproj.CRS.from_epsg(utm_epsg) # 來源是 UTM
            print(f"執行 WGS 84 UTM Zone {zone}{'S' if is_south else 'N'} -> 經緯度 轉換 (EPSG:{utm_epsg} -> EPSG:4326)")
        else:
            raise ValueError(f"不支援的大地基準: {datum_key}")

        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        lon, lat = transformer.transform(x, y)

        # 驗證轉換後的經緯度範圍
        if not (-90 <= lat <= 90):
             print(f"警告: 轉換後的緯度 {lat:.6f} 超出有效範圍 (-90 到 90)。")
             # 根據需求決定是否返回 None 或繼續
        if not (-180 <= lon <= 180):
             print(f"警告: 轉換後的經度 {lon:.6f} 超出有效範圍 (-180 到 180)。")
             # 根據需求決定是否返回 None 或繼續

        return lon, lat

    except ValueError as ve:
        messagebox.showerror("輸入錯誤", f"輸入驗證錯誤: {ve}")
        print(f"輸入驗證錯誤: {ve}")
        return None, None
    except Exception as e:
        messagebox.showerror("轉換錯誤", f"反向轉換錯誤: {e}")
        print(f"反向轉換錯誤: {e}")
        return None, None

# --- 定義常用大地基準 ---
DATUMS = {
    "WGS 84": "EPSG:4326",
    "TWD97": "EPSG:3824",
}

# --- GUI 主介面 ---
class UTMConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("雙向座標轉換工具 (pyproj)")
        self.geometry("650x650") # 增加高度以容納新元件

        style = ttk.Style(self)
        style.configure('TLabel', padding=5)
        style.configure('TEntry', padding=5)
        style.configure('TButton', padding=5)
        style.configure('TFrame', padding=10)
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))

        # Datum 選擇
        datum_frame = ttk.Frame(self, borderwidth=1, relief="solid")
        datum_frame.pack(pady=10, padx=10, fill='x')
        ttk.Label(datum_frame, text="選擇大地基準 (Datum):").pack(side=tk.LEFT, padx=5)

        self.selected_datum = tk.StringVar(value="TWD97")
        datum_combobox = ttk.Combobox(datum_frame, textvariable=self.selected_datum,
                                       values=list(DATUMS.keys()), state="readonly", width=15)
        datum_combobox.pack(side=tk.LEFT, padx=5)

        # --- 建立頁籤 ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # --- 頁籤 1: 經緯度 -> 平面座標 ---
        self.latlon_to_proj_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.latlon_to_proj_frame, text='經緯度 → 平面座標')
        self.setup_latlon_to_proj_tab()

        # --- 頁籤 2: 平面座標 -> 經緯度 ---
        self.proj_to_latlon_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.proj_to_latlon_frame, text='平面座標 → 經緯度')
        self.setup_proj_to_latlon_tab()

        # --- Google Maps 定位按鈕（移到頁籤外） ---
        self.locate_button = ttk.Button(self, text="在 Google Maps 定位", command=self.open_google_maps, state=tk.DISABLED)
        self.locate_button.pack(pady=(5, 10))

        # --- 狀態列 ---
        self.status_label = ttk.Label(self, text="請選擇轉換方向並輸入座標", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # 監控頁籤切換與經緯度輸出變化
        self.notebook.bind("<<NotebookTabChanged>>", self.update_locate_button_state)
        self.lat_label_rev.bind("<Configure>", self.update_locate_button_state)
        self.lon_label_rev.bind("<Configure>", self.update_locate_button_state)
        self.lat_entry.bind("<KeyRelease>", self.update_locate_button_state)
        self.lon_entry.bind("<KeyRelease>", self.update_locate_button_state)
        # 初始化按鈕狀態
        self.update_locate_button_state()

    def setup_latlon_to_proj_tab(self):
        """設定「經緯度 -> 平面座標」頁籤的元件"""
        frame = self.latlon_to_proj_frame

        ttk.Label(frame, text="輸入經緯度 (十進制度)", style='Header.TLabel').grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        ttk.Label(frame, text="緯度 (Latitude):").grid(row=1, column=0, sticky=tk.W)
        self.lat_entry = ttk.Entry(frame, width=20)
        self.lat_entry.grid(row=1, column=1, sticky=tk.EW)
        self.lat_entry.bind("<KeyRelease>", self.validate_gmap_input)  # 綁定驗證事件
        ttk.Label(frame, text="(-90 ~ 90)").grid(row=1, column=2, sticky=tk.W)

        ttk.Label(frame, text="經度 (Longitude):").grid(row=2, column=0, sticky=tk.W)
        self.lon_entry = ttk.Entry(frame, width=20)
        self.lon_entry.grid(row=2, column=1, sticky=tk.EW)
        self.lon_entry.bind("<KeyRelease>", self.validate_gmap_input)  # 綁定驗證事件
        ttk.Label(frame, text="(-180 ~ 180)").grid(row=2, column=2, sticky=tk.W)

        convert_btn = ttk.Button(frame, text="轉換為平面座標", command=self.perform_conversion)
        convert_btn.grid(row=3, column=0, columnspan=3, pady=15)

        ttk.Label(frame, text="輸出平面座標", style='Header.TLabel').grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 10))

        ttk.Label(frame, text="UTM/TM2 Zone:").grid(row=5, column=0, sticky=tk.W)
        self.zone_label = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.zone_label.grid(row=5, column=1, sticky=tk.EW)

        ttk.Label(frame, text="Easting (X):").grid(row=6, column=0, sticky=tk.W)
        self.easting_label = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.easting_label.grid(row=6, column=1, sticky=tk.EW)
        self.easting_label.bind("<Button-3>", self.copy_projected_coords) # 綁定右鍵點擊

        ttk.Label(frame, text="Northing (Y):").grid(row=7, column=0, sticky=tk.W)
        self.northing_label = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.northing_label.grid(row=7, column=1, sticky=tk.EW)
        self.northing_label.bind("<Button-3>", self.copy_projected_coords) # 綁定右鍵點擊

        ttk.Label(frame, text="半球 (Hemisphere):").grid(row=8, column=0, sticky=tk.W)
        self.hemi_label = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.hemi_label.grid(row=8, column=1, sticky=tk.EW)

        frame.columnconfigure(1, weight=1) # 使輸入框和標籤能隨視窗縮放

        # --- Google Maps 定位區 ---
        ttk.Separator(frame, orient='horizontal').grid(row=9, column=0, columnspan=3, sticky='ew', pady=15)
        ttk.Label(frame, text="Google Maps 定位", style='Header.TLabel').grid(row=10, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

    def setup_proj_to_latlon_tab(self):
        """設定「平面座標 -> 經緯度」頁籤的元件"""
        frame = self.proj_to_latlon_frame

        ttk.Label(frame, text="輸入平面座標", style='Header.TLabel').grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Easting (X):").grid(row=1, column=0, sticky=tk.W)
        self.easting_entry_rev = ttk.Entry(frame, width=20)
        self.easting_entry_rev.grid(row=1, column=1, sticky=tk.EW)

        ttk.Label(frame, text="Northing (Y):").grid(row=2, column=0, sticky=tk.W)
        self.northing_entry_rev = ttk.Entry(frame, width=20)
        self.northing_entry_rev.grid(row=2, column=1, sticky=tk.EW)

        ttk.Label(frame, text="UTM Zone (WGS84):").grid(row=3, column=0, sticky=tk.W)
        self.zone_entry_rev = ttk.Entry(frame, width=10)
        self.zone_entry_rev.grid(row=3, column=1, sticky=tk.W)
        ttk.Label(frame, text="(1-60, TWD97不需輸入)").grid(row=3, column=2, sticky=tk.W)

        ttk.Label(frame, text="半球 (WGS84):").grid(row=4, column=0, sticky=tk.W)
        self.hemi_var_rev = tk.StringVar(value="North")
        hemi_frame = ttk.Frame(frame)
        hemi_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W)
        ttk.Radiobutton(hemi_frame, text="北半球 (North)", variable=self.hemi_var_rev, value="North").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(hemi_frame, text="南半球 (South)", variable=self.hemi_var_rev, value="South").pack(side=tk.LEFT, padx=5)
        ttk.Label(hemi_frame, text="(TWD97不需選擇)").pack(side=tk.LEFT, padx=5)


        convert_rev_btn = ttk.Button(frame, text="轉換為經緯度", command=self.perform_reverse_conversion)
        convert_rev_btn.grid(row=5, column=0, columnspan=3, pady=15)

        ttk.Label(frame, text="輸出經緯度 (十進制度)", style='Header.TLabel').grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=(10, 10))

        ttk.Label(frame, text="緯度 (Latitude):").grid(row=7, column=0, sticky=tk.W)
        self.lat_label_rev = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.lat_label_rev.grid(row=7, column=1, sticky=tk.EW)
        self.lat_label_rev.bind("<Button-3>", self.copy_latlon_coords) # 綁定右鍵點擊

        ttk.Label(frame, text="經度 (Longitude):").grid(row=8, column=0, sticky=tk.W)
        self.lon_label_rev = ttk.Label(frame, text="-", width=20, relief=tk.SUNKEN)
        self.lon_label_rev.grid(row=8, column=1, sticky=tk.EW)
        self.lon_label_rev.bind("<Button-3>", self.copy_latlon_coords) # 綁定右鍵點擊

        frame.columnconfigure(1, weight=1) # 使輸入框和標籤能隨視窗縮放

    def perform_conversion(self):
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            datum = self.selected_datum.get()

            x, y, zone, is_south = latlon_to_projected(lat, lon, datum)

            if x is not None:
                self.zone_label.config(text=f"{zone}")
                self.easting_label.config(text=f"{x:.3f}")
                self.northing_label.config(text=f"{y:.3f}")
                self.hemi_label.config(text="South" if is_south else "North")
                self.status_label.config(text="經緯度轉換為 UTM 成功。")
            else:
                self.zone_label.config(text="-")
                self.easting_label.config(text="-")
                self.northing_label.config(text="-")
                self.hemi_label.config(text="-")
                self.status_label.config(text="經緯度轉換為 UTM 失敗。")
        except ValueError:
            messagebox.showerror("輸入錯誤", "請輸入正確的數值格式。")
        except Exception as e:
            messagebox.showerror("錯誤", f"發生未預期的錯誤: {e}")

    def perform_reverse_conversion(self):
        """處理平面座標到經緯度的轉換"""
        try:
            x = float(self.easting_entry_rev.get())
            y = float(self.northing_entry_rev.get())
            datum = self.selected_datum.get()
            zone_str = self.zone_entry_rev.get()
            is_south = self.hemi_var_rev.get() == "South"

            zone = None # 預設為 None
            if datum == 'WGS 84':
                if not zone_str:
                    raise ValueError("WGS 84 轉換需要輸入 UTM Zone。")
                try:
                    zone = int(zone_str)
                    if not (1 <= zone <= 60):
                        raise ValueError("UTM Zone 必須介於 1 到 60 之間。")
                except ValueError:
                    raise ValueError("UTM Zone 必須是有效的整數。")
            elif datum == 'TWD97':
                # TWD97 轉換不需要 zone 和 is_south，使用預設值或忽略
                zone = 0 # 或其他標記值，projected_to_latlon 內部會處理
                is_south = False # TWD97 在北半球

            lon, lat = projected_to_latlon(x, y, zone, is_south, datum)

            if lon is not None and lat is not None:
                self.lat_label_rev.config(text=f"{lat:.8f}") # 提高經緯度顯示精度
                self.lon_label_rev.config(text=f"{lon:.8f}")
                self.status_label.config(text="平面座標轉換為經緯度成功。")
            else:
                self.lat_label_rev.config(text="-")
                self.lon_label_rev.config(text="-")
                self.status_label.config(text="平面座標轉換為經緯度失敗。")

        except ValueError as ve:
            messagebox.showerror("輸入錯誤", f"請輸入正確的數值格式或檢查 UTM Zone: {ve}")
            self.status_label.config(text=f"輸入錯誤: {ve}")
        except Exception as e:
            messagebox.showerror("錯誤", f"發生未預期的錯誤: {e}")
            self.status_label.config(text=f"錯誤: {e}")

    def copy_to_clipboard(self, text_to_copy):
        '''複製文字到剪貼簿並顯示狀態訊息'''
        if text_to_copy and text_to_copy != "-":
            try:
                self.clipboard_clear()
                self.clipboard_append(text_to_copy)
                original_text = self.status_label.cget("text") # 儲存原始狀態文字
                self.status_label.config(text=f"已複製: {text_to_copy}")
                # 2秒後恢復原始狀態文字
                self.after(2000, lambda: self.status_label.config(text=original_text) if self.status_label.cget("text") == f"已複製: {text_to_copy}" else None)
            except tk.TclError:
                self.status_label.config(text="複製到剪貼簿失敗")
        else:
            self.status_label.config(text="無有效座標可複製")

    def copy_projected_coords(self, event):
        '''複製平面座標 X,Y'''
        x_val = self.easting_label.cget("text")
        y_val = self.northing_label.cget("text")
        # 檢查是否為預設的 "-"
        if x_val != "-" and y_val != "-":
            # 確保複製的是數值部分
            try:
                float(x_val)
                float(y_val)
                coords = f"{x_val},{y_val}"
                self.copy_to_clipboard(coords)
            except ValueError:
                 self.copy_to_clipboard(None) # 如果標籤內容不是有效數字
    def validate_gmap_input(self, event=None):
        """驗證上方經緯度輸入框內容並更新定位按鈕狀態"""
        lat_text = self.lat_entry.get().strip()
        lon_text = self.lon_entry.get().strip()
        is_valid = False
        try:
            if lat_text and lon_text: # 確保兩個欄位都有內容
                lat = float(lat_text)
                lon = float(lon_text)
                # 僅驗證 WGS84 範圍，因為 Google Maps 使用 WGS84
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    is_valid = True
        except ValueError:
            pass # 轉換失敗，保持 is_valid = False

        if is_valid:
            self.locate_button.config(state=tk.NORMAL)
        else:
            self.locate_button.config(state=tk.DISABLED)

    def open_google_maps(self):
        """根據目前頁籤自動抓取經緯度值開啟 Google Maps"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            lat_text = self.lat_entry.get().strip()
            lon_text = self.lon_entry.get().strip()
        else:
            lat_text = self.lat_label_rev.cget("text").strip()
            lon_text = self.lon_label_rev.cget("text").strip()
        try:
            lat = float(lat_text)
            lon = float(lon_text)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                gmap_url = f"https://www.google.com/maps?q={lat},{lon}&z=15"
                webbrowser.open(gmap_url)
                self.status_label.config(text=f"已在瀏覽器開啟 Google Maps 定位: {lat},{lon}")
            else:
                raise ValueError("座標範圍無效")
        except ValueError:
            messagebox.showerror("輸入錯誤", "無法解析有效的經緯度座標。")
            self.status_label.config(text="定位錯誤: 無法解析經緯度")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟瀏覽器: {e}")
            self.status_label.config(text=f"開啟瀏覽器錯誤: {e}")

        else:
            self.copy_to_clipboard(None) # 觸發無效座標訊息

    def copy_latlon_coords(self, event):
        '''複製經緯度 緯度,經度'''
        lat_val = self.lat_label_rev.cget("text")
        lon_val = self.lon_label_rev.cget("text")
        if lat_val != "-" and lon_val != "-":
            try:
                float(lat_val)
                float(lon_val)
                # 格式為 緯度,經度
                coords = f"{lat_val},{lon_val}"
                self.copy_to_clipboard(coords)
            except ValueError:
                 self.copy_to_clipboard(None)
        else:
            self.copy_to_clipboard(None) # 觸發無效座標訊息

    def update_locate_button_state(self, event=None):
        """根據目前頁籤的經緯度輸出自動判斷 Google Maps 定位按鈕是否可用"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            # 經緯度→平面座標頁籤，取輸入框
            try:
                lat = float(self.lat_entry.get())
                lon = float(self.lon_entry.get())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.locate_button.config(state=tk.NORMAL)
                    return
            except Exception:
                pass
        elif current_tab == 1:
            # 平面→經緯度頁籤，取輸出label
            try:
                lat = float(self.lat_label_rev.cget("text"))
                lon = float(self.lon_label_rev.cget("text"))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    self.locate_button.config(state=tk.NORMAL)
                    return
            except Exception:
                pass
        self.locate_button.config(state=tk.DISABLED)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='經緯度轉換為平面座標工具')
    parser.add_argument('--lat', type=float, help='緯度 (Latitude)')
    parser.add_argument('--lon', type=float, help='經度 (Longitude)')
    parser.add_argument('--datum', choices=DATUMS.keys(), default='TWD97', help='大地基準 (預設: TWD97)')
    # 新增反向轉換參數
    parser.add_argument('--easting', type=float, help='Easting (X) 座標')
    parser.add_argument('--northing', type=float, help='Northing (Y) 座標')
    parser.add_argument('--zone', type=int, help='UTM Zone (WGS 84 必填)')
    parser.add_argument('--south', action='store_true', help='指定為南半球 (WGS 84)')

    args, unknown = parser.parse_known_args()

    # 判斷執行哪個方向的轉換
    if args.lat is not None and args.lon is not None:
        # 經緯度 -> 平面
        x, y, zone_out, is_south_out = latlon_to_projected(args.lat, args.lon, args.datum)
        if x is not None:
            print(f"Datum: {args.datum}")
            print(f"Zone: {zone_out}{'S' if is_south_out else 'N'}")
            print(f"Easting (X): {x:.3f}")
            print(f"Northing (Y): {y:.3f}")
        else:
            print("經緯度轉換為平面座標失敗。")
    elif args.easting is not None and args.northing is not None:
        # 平面 -> 經緯度
        if args.datum == 'WGS 84' and args.zone is None:
            print("錯誤：使用 WGS 84 進行反向轉換時，必須提供 --zone 參數。")
            sys.exit(1)
        # TWD97 不需要 zone 和 south，projected_to_latlon 會處理
        zone_in = args.zone if args.datum == 'WGS 84' else 0 # 提供預設值給 TWD97
        is_south_in = args.south if args.datum == 'WGS 84' else False

        lon, lat = projected_to_latlon(args.easting, args.northing, zone_in, is_south_in, args.datum)
        if lon is not None:
            print(f"Datum: {args.datum}")
            if args.datum == 'WGS 84':
                 print(f"Input Zone: {zone_in}{'S' if is_south_in else 'N'}")
            print(f"Longitude: {lon:.8f}")
            print(f"Latitude: {lat:.8f}")
        else:
            print("平面座標轉換為經緯度失敗。")
    else:
        app = UTMConverterApp()
        app.mainloop()