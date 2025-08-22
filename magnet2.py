# --- GEREKLİ KÜTÜPHANELER ---
import tkinter as tk
import sys
import time
import threading
import statistics
from gpiozero import OutputDevice, InputDevice, Device
from gpiozero.pins.lgpio import LGPIOFactory

# --- GPIO MOTORUNU ZORUNLU OLARAK AYARLA ---
Device.pin_factory = LGPIOFactory()

# ==========================================================================================
# YENİ HX711 SINIFI (Sadece gpiozero kullanır, harici kütüphane yok)
# ==========================================================================================
class HX711_gpiozero:
    def __init__(self, dout_pin, sck_pin, gain=128):
        self.sck = OutputDevice(sck_pin)
        self.dout = InputDevice(dout_pin)
        self.OFFSET = 0
        self.REFERENCE_UNIT = 1
        self.last_val = 0
        
        self.GAIN = 0
        self.set_gain(gain)
        
        self.sck.off()
        time.sleep(0.1)

    def is_ready(self):
        return self.dout.value == 0

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        
        self.sck.off()
        self.read()

    def read(self):
        while not self.is_ready():
            time.sleep(0.01)

        data = 0
        for _ in range(24):
            self.sck.on()
            self.sck.off()
            data = (data << 1) | self.dout.value

        for _ in range(self.GAIN):
            self.sck.on()
            self.sck.off()

        # 2's complement conversion
        if data & 0x800000:
            data |= ~0xFFFFFF
        
        self.last_val = data
        return data

    def read_average(self, times=3):
        values = []
        for _ in range(times):
            values.append(self.read())
            time.sleep(0.01)
        return statistics.mean(values)

    def get_value(self, times=3):
        return self.read_average(times) - self.OFFSET

    def get_weight(self, times=3):
        value = self.get_value(times)
        return value / self.REFERENCE_UNIT

    def tare(self, times=15):
        self.OFFSET = self.read_average(times)

    def set_reference_unit(self, reference_unit):
        self.REFERENCE_UNIT = reference_unit
# ==========================================================================================
# YENİ HX711 SINIFI SONU
# ==========================================================================================

# --- PIN TANIMLAMALARI ---
EM_PIN_1 = 17
EM_PIN_2 = 2
HX711_1_DT_PIN = 5
HX711_1_SCK_PIN = 6
HX711_2_DT_PIN = 23
HX711_2_SCK_PIN = 24

# --- CİHAZ KURULUMU ---
em_1 = OutputDevice(EM_PIN_1, initial_value=False)
em_2 = OutputDevice(EM_PIN_2, initial_value=False)

# DEĞİŞİKLİK: Yeni HX711_gpiozero sınıfımızı kullanıyoruz
hx1 = HX711_gpiozero(dout_pin=HX711_1_DT_PIN, sck_pin=HX711_1_SCK_PIN)
reference_unit_1 = -430  # SENSÖR 1 İÇİN KENDİ KALİBRASYON DEĞERİNİZİ GİRİN
hx1.set_reference_unit(reference_unit_1)
hx1.tare()
print("Sensör 1 için dara alma tamamlandı.")

hx2 = HX711_gpiozero(dout_pin=HX711_2_DT_PIN, sck_pin=HX711_2_SCK_PIN)
reference_unit_2 = -450  # SENSÖR 2 İÇİN KENDİ KALİBRASYON DEĞERİNİZİ GİRİN
hx2.set_reference_unit(reference_unit_2)
hx2.tare()
print("Sensör 2 için dara alma tamamlandı.")

# --- ARKA PLAN THREAD İÇİN DURDURMA OLAYI ---
stop_threads = threading.Event()

# --- FONKSİYONLAR ---
def toggle_em1():
    em_1.toggle()
    if em_1.is_active:
        btn_pin17.config(text=f"Elektromagnet 1'i KAPAT", bg="#f44336")
    else:
        btn_pin17.config(text=f"Elektromagnet 1'i AÇ", bg="#4CAF50")

def toggle_em2():
    em_2.toggle()
    if em_2.is_active:
        btn_pin2.config(text=f"Elektromagnet 2'yi KAPAT", bg="#f44336")
    else:
        btn_pin2.config(text=f"Elektromagnet 2'yi AÇ", bg="#4CAF50")

def read_weights():
    while not stop_threads.is_set():
        try:
            weight1 = hx1.get_weight(5)
            weight2 = hx2.get_weight(5)
            root.after(0, lambda: weight1_label.config(text=f"Sensör 1 Ağırlık: {weight1:.2f} g"))
            root.after(0, lambda: weight2_label.config(text=f"Sensör 2 Ağırlık: {weight2:.2f} g"))
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            break
    print("Ağırlık okuma durduruldu.")

def on_closing():
    print("Program kapatılıyor...")
    stop_threads.set()
    if 'weight_thread' in globals() and weight_thread.is_alive():
        weight_thread.join()
    em_1.close()
    em_2.close()
    root.destroy()
    sys.exit()

# --- GUI KURULUMU ---
root = tk.Tk()
root.title("Kontrol Paneli")
root.geometry("450x400")
root.configure(bg="#f0f0f0")
weight_frame = tk.Frame(root, bg="#f0f0f0")
weight_frame.pack(pady=20)
weight1_label = tk.Label(weight_frame, text="Sensör 1 Ağırlık: Hesaplanıyor...", font=("Helvetica", 16), bg="#e3f2fd", padx=10, pady=5)
weight1_label.pack(pady=5)
weight2_label = tk.Label(weight_frame, text="Sensör 2 Ağırlık: Hesaplanıyor...", font=("Helvetica", 16), bg="#e8f5e9", padx=10, pady=5)
weight2_label.pack(pady=5)
button_frame = tk.Frame(root, bg="#f0f0f0")
button_frame.pack(pady=20)
btn_pin17 = tk.Button(button_frame, text="Elektromagnet 1'i AÇ", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=toggle_em1, width=25, height=2)
btn_pin17.pack(pady=10)
btn_pin2 = tk.Button(button_frame, text="Elektromagnet 2'yi AÇ", font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", command=toggle_em2, width=25, height=2)
btn_pin2.pack(pady=10)

# --- THREAD'İ BAŞLATMA ---
weight_thread = threading.Thread(target=read_weights)
weight_thread.daemon = True
weight_thread.start()

# --- PENCERE KAPATMA OLAYI ---
root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()