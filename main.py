import os
import shutil
import streamlit as st
from random import randint
import subprocess
import wave
import json
import cv2
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import speech_recognition as sr
import random


def download_video(youtube_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube usando yt-dlp e retorna o caminho do arquivo baixado.
    """
    try:
        import yt_dlp

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        ydl_opts = {
            'format': 'best[ext=mp4]',  # Seleciona o melhor formato em mp4
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),  # Nome do arquivo
            'retries': 10,  # Realiza até 10 tentativas em caso de falha
            'fragment_retries': 10,  # Retries para fragmentos
            'http_chunk_size': 1024 * 1024,  # Download em fragmentos de 1MB
            'noprogress': True,  # Desabilita barra de progresso para reduzir logs
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None


def get_video_duration(video_path):
    """
    Usa ffprobe para obter a duração total do vídeo.
    """
    try:
        ffprobe_path = "ffprobe"
        result = subprocess.run(
            [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        raise RuntimeError(f"Erro ao obter a duração do vídeo: {e}")


def summarize_description(description, max_words=5):
    """
    Resume uma descrição pegando as primeiras palavras relevantes.
    """
    words = description.split()
    return " ".join(words[:max_words]).capitalize()


def generate_hashtags(description, max_tags=5):
    """
    Gera hashtags aleatórias com palavras maiores que 10 letras.
    """
    words = [word for word in description.split() if len(word) > 10]
    random.shuffle(words)  # Mistura as palavras
    hashtags = ["#" + word.lower() for word in words[:max_tags]]
    return " ".join(hashtags)


def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
    """
    Gera cortes de vídeo a partir de um vídeo original, utilizando ffmpeg para processar.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        video_duration = get_video_duration(video_path)
        clips = []
        progress_bar = st.progress(0)

        for i in range(num_clips):
            start_time = randint(0, int(video_duration - clip_length - 1))
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")

            ffmpeg_command = [
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(start_time), "-t", str(clip_length),
                "-c:v", "libx264", "-c:a", "aac"
            ]

            # Ajuste da proporção
            if aspect_ratio == "9:16":
                ffmpeg_command += ["-vf", "crop=in_h*9/16:in_h"]
            
            ffmpeg_command.append(output_file)

            subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            clips.append((output_file, start_time))
            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None


def extract_thumbnail(video_path, start_time, output_path="thumbnails"):
    """
    Extrai uma imagem de pré-visualização do clipe no início do vídeo.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    thumbnail_path = os.path.join(output_path, f"thumbnail_{os.path.basename(video_path)}.jpg")
    with VideoFileClip(video_path) as video:
        frame = video.get_frame(start_time)
        image = Image.fromarray(frame)
        image.save(thumbnail_path)
    return thumbnail_path


def transcribe_audio_with_google(audio_path):
    """
    Transcreve o áudio de um arquivo usando SpeechRecognition com a API do Google.
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="pt-BR")
    except sr.UnknownValueError:
        return "A transcrição não pôde ser realizada. Áudio inaudível ou não claro."
    except sr.RequestError as e:
        st.error(f"Erro na API do Google: {e}")
        return "Erro ao usar a API do Google. Verifique sua conexão com a internet."
    except Exception as e:
        st.error(f"Erro ao transcrever áudio com Google SpeechRecognition: {e}")
        return "Transcrição indisponível."


def add_subtitles_with_opencv(video_path, transcription, start_time, clip_length, output_path):
    """
    Adiciona legendas diretamente no vídeo usando OpenCV.
    """
    try:
        # Abrir vídeo
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_video = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

        # Processar frames e adicionar legenda
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        text_position = (int(width * 0.1), int(height * 0.9))  # Posição do texto

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Adicionar legenda apenas durante o clipe
            current_time = frame_count / fps
            if start_time <= current_time <= (start_time + clip_length):
                cv2.putText(
                    frame, transcription, text_position, cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1, color=(255, 255, 255), thickness=2, lineType=cv2.LINE_AA
                )

            out.write(frame)
            frame_count += 1
            if frame_count >= total_frames:
                break

        cap.release()
        out.release()
        return output_video
    except Exception as e:
        st.error(f"Erro ao adicionar legendas com OpenCV: {e}")
        return None


def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    youtube_url = st.text_input("Link do vídeo do YouTube", "")
    clip_length = st.selectbox("Escolha a duração dos cortes (em segundos)", [30, 40, 60, 80])
    aspect_ratio = st.selectbox("Escolha a proporção dos cortes", ["16:9", "9:16"])

    if st.button("Gerar Cortes"):
        if not youtube_url:
            st.error("Por favor, insira um link válido do YouTube.")
            return

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(youtube_url)

        if video_path:
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length, aspect_ratio)
                if clips:
                    st.session_state["clips"] = clips
                    st.success("Cortes gerados com sucesso!")
                else:
                    st.error("Erro ao gerar os cortes.")

    if "clips" in st.session_state and st.session_state["clips"]:
        st.write("Baixe os cortes abaixo com prévias e legendas:")
        for i, (clip, start_time) in enumerate(st.session_state["clips"], start=1):
            thumbnail = extract_thumbnail(clip, start_time)

            # Converter para WAV para usar no SpeechRecognition
            wav_file = f"{os.path.splitext(clip)[0]}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", clip, "-ac", "1", "-ar", "16000", wav_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            transcription = transcribe_audio_with_google(wav_file)
            short_title = summarize_description(transcription)
            hashtags = generate_hashtags(transcription)
            clip_name = f"{short_title.replace(' ', '_')}_{i}.mp4"

            # Adicionar legendas ao vídeo usando OpenCV
            subtitled_clip = add_subtitles_with_opencv(clip, transcription, start_time, clip_length, clip)

            if subtitled_clip:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(thumbnail, caption=f"Corte {i}", use_container_width=True)
                with col2:
                    st.subheader(f"Título Sugerido: {short_title}")
                    st.write(f"Descrição: {transcription}")
                    st.write(f"Hashtags: {hashtags}")
                    with open(subtitled_clip, "rb") as f:
                        st.download_button(
                            label=f"Baixar {clip_name} com Legendas",
                            data=f,
                            file_name=clip_name,
                            mime="video/mp4"
                        )
            else:
                st.error(f"Não foi possível adicionar legendas ao vídeo {clip_name}.")


if __name__ == "__main__":
    main()
