import tkinter as tk
import RPi.GPIO as GPIO
import sys
import time
import threading

try:
    # hx711 kütüphanesini içe aktar
    from hx711 import HX711
except ImportError:
    # Kütüphane bulunamazsa hata mesajı yazdır ve çık
    print("Hata: 'hx711' kütüphanesi bulunamadı.")
    print("Lütfen 'pip install hx711' komutu ile kurun.")
    sys.exit()

# GPIO pin numaralarını tanımla
EM_PIN_1 = 17
EM_PIN_2 = 2

HX711_1_DT_PIN = 5
HX711_1_SCK_PIN = 6

HX711_2_DT_PIN = 23
HX711_2_SCK_PIN = 24

# GPIO uyarılarını devre dışı bırak ve pin modunu ayarla
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Elektromagnet pinlerini çıkış olarak ayarla
GPIO.setup(EM_PIN_1, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(EM_PIN_2, GPIO.OUT, initial=GPIO.LOW)

# --- Sensör 1 Kurulumu ---
hx1 = HX711(dout_pin=HX711_1_DT_PIN, pd_sck_pin=HX711_1_SCK_PIN)
# !!! SENSÖR 1 İÇİN KALİBRASYON DEĞERİNİ BURAYA GİRİN !!!
reference_unit_1 = -430  # Örnek değer, kendi değerinizle değiştirin
hx1.set_reference_unit(reference_unit_1)
hx1.reset()
hx1.tare()
print("Sensör 1 için dara alma tamamlandı.")

# --- Sensör 2 Kurulumu ---
hx2 = HX711(dout_pin=HX711_2_DT_PIN, pd_sck_pin=HX711_2_SCK_PIN)
# !!! SENSÖR 2 İÇİN KALİBRASYON DEĞERİNİ BURAYA GİRİN !!!
reference_unit_2 = -450  # Örnek değer, kendi değerinizle değiştirin
hx2.set_reference_unit(reference_unit_2)
hx2.reset()
hx2.tare()
print("Sensör 2 için dara alma tamamlandı.")

# Pin durumlarını takip etmek için boolean değişkenler
is_pin17_on = False
is_pin2_on = False
# Arka plan iş parçacıklarını durdurmak için olay nesnesi
stop_threads = threading.Event()

def toggle_pin17():
    """Elektromagnet 1'i açıp kapatır ve butonun durumunu günceller."""
    global is_pin17_on
    is_pin17_on = not is_pin17_on
    if is_pin17_on:
        GPIO.output(EM_PIN_1, GPIO.HIGH)
        btn_pin17.config(text="Elektromagnet 1'i KAPAT", bg="#f44336")
    else:
        GPIO.output(EM_PIN_1, GPIO.LOW)
        btn_pin17.config(text="Elektromagnet 1'i AÇ", bg="#4CAF50")

def toggle_pin2():
    """Elektromagnet 2'yi açıp kapatır ve butonun durumunu günceller."""
    global is_pin2_on
    is_pin2_on = not is_pin2_on
    if is_pin2_on:
        GPIO.output(EM_PIN_2, GPIO.HIGH)
        btn_pin2.config(text="Elektromagnet 2'yi KAPAT", bg="#f44336")
    else:
        GPIO.output(EM_PIN_2, GPIO.LOW)
        btn_pin2.config(text="Elektromagnet 2'yi AÇ", bg="#4CAF50")

def read_weights():
    """Arka planda sürekli ağırlıkları okur ve GUI'yi günceller."""
    while not stop_threads.is_set():
        try:
            # Sensör 1'den ağırlığı oku
            weight1 = hx1.get_weight(5)
            
            # Sensör 2'den ağırlığı oku
            weight2 = hx2.get_weight(5)
            
            # Etiketlerin metnini ana iş parçacığında güvenli bir şekilde güncelle
            root.after(0, lambda: weight1_label.config(text=f"Sensör 1 Ağırlık: {weight1:.2f} g"))
            root.after(0, lambda: weight2_label.config(text=f"Sensör 2 Ağırlık: {weight2:.2f} g"))
            
            # CPU kullanımını azaltmak için kısa bir bekleme
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            break
    print("Ağırlık okuma durduruldu.")

def on_closing():
    """Pencere kapatıldığında çağrılır, kaynakları temizler ve programı sonlandırır."""
    print("Program kapatılıyor...")
    stop_threads.set()  # Ağırlık okuma döngüsünü durdur
    weight_thread.join() # İş parçacığının bitmesini bekle
    GPIO.cleanup()      # GPIO pinlerini temizle
    root.destroy()      # Tkinter penceresini yok et
    sys.exit()          # Programdan çık

# --- Tkinter GUI Kurulumu ---
root = tk.Tk()
root.title("Kontrol Paneli")
root.geometry("450x400")
root.configure(bg="#f0f0f0")

# Ağırlık etiketleri için çerçeve
weight_frame = tk.Frame(root, bg="#f0f0f0")
weight_frame.pack(pady=20)

weight1_label = tk.Label(weight_frame, text="Sensör 1 Ağırlık: Hesaplanıyor...", font=("Helvetica", 16), bg="#e3f2fd", padx=10, pady=5)
weight1_label.pack(pady=5)

weight2_label = tk.Label(weight_frame, text="Sensör 2 Ağırlık: Hesaplanıyor...", font=("Helvetica", 16), bg="#e8f5e9", padx=10, pady=5)
weight2_label.pack(pady=5)

# Kontrol butonları için çerçeve
button_frame = tk.Frame(root, bg="#f0f0f0")
button_frame.pack(pady=20)

btn_pin17 = tk.Button(button_frame, text="Elektromagnet 1'i AÇ", font=("Helvetica", 12, "bold"),
                      bg="#4CAF50", fg="white", command=toggle_pin17, width=25, height=2)
btn_pin17.pack(pady=10)

btn_pin2 = tk.Button(button_frame, text="Elektromagnet 2'yi AÇ", font=("Helvetica", 12, "bold"),
                     bg="#4CAF50", fg="white", command=toggle_pin2, width=25, height=2)
btn_pin2.pack(pady=10)

# Ağırlık okuma iş parçacığını başlat
weight_thread = threading.Thread(target=read_weights)
weight_thread.daemon = True # Ana program kapanınca bu thread de kapansın
weight_thread.start()

# Pencere kapatma protokolünü ayarla
root.protocol("WM_DELETE_WINDOW", on_closing)

# Tkinter ana döngüsünü başlat
root.mainloop()
