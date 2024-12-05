import os
import streamlit as st
from random import randint
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube

def download_video(youtube_url, output_path="downloads"):
    """
    Faz o download de um vídeo do YouTube usando pytube e retorna o caminho do arquivo baixado.
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        yt = YouTube(youtube_url)
        stream = yt.streams.filter(file_extension='mp4', res="720p", progressive=True).first()
        video_path = stream.download(output_path)
        return video_path
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None


def get_transcription(video_id):
    """
    Obtém a transcrição de um vídeo do YouTube usando a YouTubeTranscriptAPI.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["pt", "en"])
        return transcript
    except Exception as e:
        st.error(f"Erro ao obter transcrição: {e}")
        return None


def create_srt_file(transcription, output_srt):
    """
    Cria um arquivo de legendas SRT a partir de uma transcrição.
    """
    try:
        with open(output_srt, "w") as srt_file:
            for i, item in enumerate(transcription):
                start_time = item["start"]
                duration = item["duration"]
                end_time = start_time + duration

                start_time_str = time_to_srt_format(start_time)
                end_time_str = time_to_srt_format(end_time)

                srt_file.write(f"{i + 1}\n")
                srt_file.write(f"{start_time_str} --> {end_time_str}\n")
                srt_file.write(f"{item['text']}\n\n")
        return output_srt
    except Exception as e:
        st.error(f"Erro ao criar arquivo SRT: {e}")
        return None


def time_to_srt_format(seconds):
    """
    Converte tempo em segundos para o formato SRT (hh:mm:ss,ms).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"


def add_subtitles_to_video(video_path, srt_path, output_path):
    """
    Adiciona legendas ao vídeo usando FFmpeg.
    """
    try:
        output_video = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        ffmpeg_command = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={os.path.abspath(srt_path)}",
            output_video
        ]

        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            st.error(f"Erro no FFmpeg ao adicionar legendas: {result.stderr}")
            return None

        return output_video
    except Exception as e:
        st.error(f"Erro ao adicionar legendas com FFmpeg: {e}")
        return None


def main():
    st.title("Gerador de Cortes Virais para YouTube com Legendas")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos com legendas automaticamente!")

    youtube_url = st.text_input("Link do vídeo do YouTube", "")

    if st.button("Gerar Legendas e Vídeo"):
        if not youtube_url:
            st.error("Por favor, insira um link válido do YouTube.")
            return

        # Extrair o ID do vídeo
        video_id = youtube_url.split("v=")[-1].split("&")[0]

        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(youtube_url)

        if video_path:
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Obtendo transcrição..."):
                transcription = get_transcription(video_id)

            if transcription:
                st.success("Transcrição obtida com sucesso!")
                output_srt = os.path.join("downloads", f"{video_id}.srt")
                srt_path = create_srt_file(transcription, output_srt)

                if srt_path:
                    with st.spinner("Adicionando legendas ao vídeo..."):
                        subtitled_video = add_subtitles_to_video(video_path, srt_path, video_path)

                    if subtitled_video:
                        st.success("Legendas adicionadas com sucesso!")
                        with open(subtitled_video, "rb") as f:
                            st.download_button(
                                label="Baixar vídeo com legendas",
                                data=f,
                                file_name=os.path.basename(subtitled_video),
                                mime="video/mp4"
                            )
                    else:
                        st.error("Erro ao adicionar legendas ao vídeo.")
            else:
                st.error("Erro ao obter a transcrição.")
        else:
            st.error("Erro ao baixar o vídeo.")


if __name__ == "__main__":
    main()
