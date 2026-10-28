"""Make MuseTalk runnable without mmpose and without librosa.

- mmpose needs mmcv, which has to be compiled against this torch. The pose
  is only used to work out where the face is in the frame; the frame's own
  face detector does that well enough, so the pose is left out and the
  detected box is widened upwards to include the forehead.
- librosa needs numba, which does not run on this numpy. Loading a wav is
  a one-liner with soundfile, which is already here.
"""
from pathlib import Path

# 1) the pose is optional
p = Path(r"E:\\musetalk\\musetalk\\utils\\preprocessing.py")
s = p.read_text(encoding="utf-8")
old = """from mmpose.apis import inference_topdown, init_model
from mmpose.structures import merge_data_samples"""
new = """try:
    from mmpose.apis import inference_topdown, init_model
    from mmpose.structures import merge_data_samples
    HAS_MMPOSE = True
except Exception:  # noqa: BLE001 - mmcv has to match torch, so it is often absent
    HAS_MMPOSE = False"""
assert old in s, "mmpose 导入锚点没找到"
s = s.replace(old, new, 1)

old = """    for fb in tqdm(batches):
        results = inference_topdown(model, np.asarray(fb)[0])
        results = merge_data_samples(results)
        keypoints = results.pred_instances.keypoints
        face_land_mark= keypoints[0][23:91]
        face_land_mark = face_land_mark.astype(np.int32)
        """
new = """    for fb in tqdm(batches):
        if HAS_MMPOSE:
            results = inference_topdown(model, np.asarray(fb)[0])
            results = merge_data_samples(results)
            keypoints = results.pred_instances.keypoints
            face_land_mark= keypoints[0][23:91]
            face_land_mark = face_land_mark.astype(np.int32)
        else:
            face_land_mark = None
        """
assert old in s, "推理锚点没找到"
s = s.replace(old, new, 1)

old = """            half_face_coord =  face_land_mark[29]#np.mean([face_land_mark[28], face_land_mark[29]], axis=0)
            range_minus = (face_land_mark[30]- face_land_mark[29])[1]
            range_plus = (face_land_mark[29]- face_land_mark[28])[1]
            average_range_minus.append(range_minus)
            average_range_plus.append(range_plus)
            if upperbondrange != 0:
                half_face_coord[1] = upperbondrange+half_face_coord[1] #手动调整  + 向下（偏29）  - 向上（偏28）
            half_face_dist = np.max(face_land_mark[:,1]) - half_face_coord[1]
            min_upper_bond = 0
            upper_bond = max(min_upper_bond, half_face_coord[1] - half_face_dist)
            
            f_landmark = (np.min(face_land_mark[:, 0]),int(upper_bond),np.max(face_land_mark[:, 0]),np.max(face_land_mark[:,1]))
            x1, y1, x2, y2 = f_landmark
            
            if y2-y1<=0 or x2-x1<=0 or x1<0: # if the landmark bbox is not suitable, reuse the bbox
                coords_list += [f]
                w,h = f[2]-f[0], f[3]-f[1]
                print("error bbox:",f)
            else:
                coords_list += [f_landmark]"""
new = """            if face_land_mark is None:
                # no pose model: the detected box, widened upwards so that
                # the forehead is in the crop as well
                x1, y1, x2, y2 = f
                h = y2 - y1
                upper_bond = int(max(0, y1 - 0.45 * h))
                f_landmark = (int(x1), upper_bond, int(x2), int(y2))
                coords_list += [f_landmark]
                continue
            half_face_coord =  face_land_mark[29]#np.mean([face_land_mark[28], face_land_mark[29]], axis=0)
            range_minus = (face_land_mark[30]- face_land_mark[29])[1]
            range_plus = (face_land_mark[29]- face_land_mark[28])[1]
            average_range_minus.append(range_minus)
            average_range_plus.append(range_plus)
            if upperbondrange != 0:
                half_face_coord[1] = upperbondrange+half_face_coord[1] #手动调整  + 向下（偏29）  - 向上（偏28）
            half_face_dist = np.max(face_land_mark[:,1]) - half_face_coord[1]
            min_upper_bond = 0
            upper_bond = max(min_upper_bond, half_face_coord[1] - half_face_dist)

            f_landmark = (np.min(face_land_mark[:, 0]),int(upper_bond),np.max(face_land_mark[:, 0]),np.max(face_land_mark[:,1]))
            x1, y1, x2, y2 = f_landmark

            if y2-y1<=0 or x2-x1<=0 or x1<0: # if the landmark bbox is not suitable, reuse the bbox
                coords_list += [f]
                w,h = f[2]-f[0], f[3]-f[1]
                print("error bbox:",f)
            else:
                coords_list += [f_landmark]"""
assert old in s, "框计算锚点没找到"
s = s.replace(old, new, 1)

# the model is only loaded when the pose is available
old = """model = init_model(config_file, checkpoint_file, device=device)"""
new = """model = init_model(config_file, checkpoint_file, device=device) if HAS_MMPOSE else None"""
assert old in s, "model 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("preprocessing.py 已改（不用 mmpose）")

# 2) librosa is not needed to read a wav
p = Path(r"E:\\musetalk\\musetalk\\utils\\audio_processor.py")
s = p.read_text(encoding="utf-8")
old = "import librosa"
new = """try:
    import librosa
except Exception:  # noqa: BLE001 - librosa needs numba, which needs an old numpy
    librosa = None"""
assert old in s, "librosa 导入锚点没找到"
s = s.replace(old, new, 1)

old = "    librosa_output, sampling_rate = librosa.load(wav_path, sr=16000)"
new = """    if librosa is not None:
        librosa_output, sampling_rate = librosa.load(wav_path, sr=16000)
    else:
        import soundfile as sf
        from scipy.signal import resample_poly
        data, sr = sf.read(wav_path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != 16000:
            g = math.gcd(int(sr), 16000)
            data = resample_poly(data, 16000 // g, sr // g)
        librosa_output = np.asarray(data, dtype=np.float32)
        sampling_rate = 16000"""
assert old in s, "librosa.load 锚点没找到"
s = s.replace(old, new, 1)
if "\nimport numpy as np" not in s:
    s = s.replace("import math", "import math\nimport numpy as np", 1)
p.write_text(s, encoding="utf-8")
print("audio_processor.py 已改（不用 librosa）")
