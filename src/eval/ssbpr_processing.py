import glob as gb
import argparse
import librosa
import collections
import numpy as np
from sklearn.model_selection import train_test_split
import random
import csv
from tqdm import tqdm
import os
from src.util import get_entire_signal_librosa

data_dir = "datasets/SSBPR/"
feature_dir = "feature/snoring_eval/"
audio_dir = data_dir + "female"
if not os.path.exists(audio_dir):
    raise FileNotFoundError(f"Folder not found: {audio_dir}, please download the dataset.")

def preprocess_split():
    female_user_list = set()
    male_user_list = set()
    sound_dir_loc = np.array(gb.glob(data_dir + "*/*/*.wav"))

    audio_split = []
    labels = []
    filename_list = []
    
    for file in sound_dir_loc:
        userID = file.split("/")[-1][:9]
        sex = file.split("/")[-3]
        if sex == "female":
            female_user_list.add(userID)
        elif sex == "male":
            male_user_list.add(userID)
    female_user_list = list(female_user_list)
    male_user_list = list(male_user_list)
    print(female_user_list, male_user_list)
    np.random.shuffle(female_user_list)
    np.random.shuffle(male_user_list)

    num_folds = 5
    fold_size = 2
    user_folds = [female_user_list[i*fold_size:(i+1)*fold_size] + male_user_list[i*fold_size:(i+1)*fold_size] for i in range(num_folds)]
    # Print the folds
    for i, fold in enumerate(user_folds):
        print(f"Fold {i+1}: {fold}")
    
    for file in sound_dir_loc:
        label = int(file.split(".")[0][-1])
        if label == 5: continue
        u = file.split("/")[-1][:9]
        for i, fold in enumerate(user_folds):
            if u in fold:
                audio_split.append(i)
                break
        labels.append(label)
        filename_list.append(file)

    np.save(feature_dir + "split.npy", audio_split)
    np.save(feature_dir + "labels.npy", labels)
    np.save(feature_dir + "sound_dir_loc.npy", filename_list)


def check_demographic():
    num_folds = 5
    data_folds = np.load(feature_dir + "split.npy")
    labels = np.load(feature_dir + "labels.npy")
    # Iterate through each fold
    for fold in range(num_folds):
        fold_indices = np.where(data_folds == fold)[0]  # Indices of data points in the current fold
        fold_labels = labels[fold_indices]  # Labels of data points in the current fold
        unique_labels, label_counts = np.unique(fold_labels, return_counts=True)  # Unique labels and their counts
        print(f"Fold {fold} label distribution:")
        for label, count in zip(unique_labels, label_counts):
            print(f"Label {label}: {count} samples")
        print()


def extract_and_save_embeddings_baselines(feature="opensmile"):
    from baseline.extract_feature import extract_opensmile_features, extract_vgg_feature, extract_clap_feature, extract_audioMAE_feature
    
    sound_dir_loc = np.load(feature_dir + "sound_dir_loc.npy")

    if feature == "opensmile":
        opensmile_features = []
        for file in tqdm(sound_dir_loc):
            audio_signal, sr = librosa.load(file, sr=16000)
            opensmile_feature = extract_opensmile_features(file)
            opensmile_features.append(opensmile_feature)
        np.save(feature_dir + "opensmile_feature.npy", np.array(opensmile_features))
    
    elif feature == "vggish":
        vgg_features = extract_vgg_feature(sound_dir_loc)
        np.save(feature_dir + "vggish_feature.npy", np.array(vgg_features))
    elif feature == "clap":
        clap_features = extract_clap_feature(sound_dir_loc)
        np.save(feature_dir + "clap_feature.npy", np.array(clap_features))
    elif feature == "audiomae":
        audiomae_feature = extract_audioMAE_feature(sound_dir_loc)
        np.save(feature_dir + "audiomae_feature.npy", np.array(audiomae_feature))


def process_spectrogram(input_sec=2):
    audio_images = []
    sound_dir_loc = np.load(feature_dir + "sound_dir_loc.npy")
    for file in tqdm(sound_dir_loc):
        data = get_entire_signal_librosa("", file[:-4], spectrogram=True, pad=True, input_sec=input_sec)
        audio_images.append(data)
    np.savez(feature_dir + "spec.npz", *audio_images)


def extract_and_save_embeddings(feature="covid", dim=1280):
    from src.eval.model_util import extract_opera_feature
    audio_images = np.load(feature_dir + "spec.npz")
    audio_images = [audio_images[f] for f in audio_images.files]
    cola_features = extract_opera_feature(audio_images,  pretrain=feature, from_spec=True, dim=dim)
    feature += str(dim)
    np.save(feature_dir + feature + "_feature.npy", np.array(cola_features))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrain", type=str, default="operaCE")
    parser.add_argument("--dim", type=int, default=1280)
    args = parser.parse_args()
    if not os.path.exists(feature_dir):
        os.makedirs(feature_dir)
        preprocess_split()
        check_demographic()
        process_spectrogram()

    if args.pretrain in ["vggish", "opensmile", "clap", "audiomae"]: 
        extract_and_save_embeddings_baselines(args.pretrain)
    else:
        extract_and_save_embeddings(args.pretrain, dim=args.dim)