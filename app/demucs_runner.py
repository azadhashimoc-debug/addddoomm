import torchaudio
import torch
import soundfile as sf
import numpy as np
import sys
import os

# torchaudio.save funksiyasını TAMAMİLE ENİSİ İLE EVZ EDİRİK
# Bu yamaq Windows-da TorchCodec xətasını kökündən həll edir
def patched_save(uri, src, sample_rate, **kwargs):
    try:
        # Tensoru emal edilə bilən formata salırıq
        if isinstance(src, torch.Tensor):
            data = src.detach().cpu().numpy()
        else:
            data = src

        # Demucs (Kanallar, Uzunluq) formatında verir, soundfile (Uzunluq, Kanallar) tələb edir
        if data.ndim == 2:
            data = data.T

        # Faylın qovluğunun mövcud olduğundan əmin oluruq
        os.makedirs(os.path.dirname(uri), exist_ok=True)

        # Birbaşa soundfile vasitəsilə yadda saxlayırıq
        sf.write(uri, data, sample_rate)
        print(f"--- [OK] Fayl yadda saxlanıldı: {os.path.basename(uri)}")
        return True
    except Exception as e:
        print(f"--- [ERROR] Fayl yazılarkən xəta: {e}")
        return False

# Orijinal funksiyanı yamaqlayırıq
torchaudio.save = patched_save

# Demucs-un əsas funksiyasını çağırırıq
from demucs.separate import main

if __name__ == "__main__":
    main()
