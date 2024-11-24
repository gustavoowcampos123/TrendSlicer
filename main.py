import os
import streamlit as st
from pytube import YouTube
from moviepy.video.io.VideoFileClip import VideoFileClip
from random import randint

def download_video(youtube_url, output_path="downloads"):
    try:
        yt = YouTube(youtube_url)
        stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        stream.download(output_path)
        return os.path.join(output_path, stream.default_filename)
    except Exception as e:
        st.error(f"Erro ao baixar o vídeo: {e}")
        return None

def generate_clips(video_path, clip_length, num_clips=10, output_path="cuts"):
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        video = VideoFileClip(video_path)
        video_duration = int(video.duration)

        clips = []
        for i in range(num_clips):
            start_time = randint(0, video_duration - clip_length - 1)
            end_time = start_time + clip_length
            clip = video.subclip(start_time, end_time)
            output_file = os.path.join(output_path, f"clip_{i + 1}.mp4")
            clip.write_videofile(output_file, codec="libx264")
            clips.append(output_file)
        
        video.close()
        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None

def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    # Entrada do link do vídeo
    youtube_url = st.text_input("Link do vídeo do YouTube", "")

    # Seleção da duração dos cortes
    clip_length = st.selectbox("Escolha a duração dos cortes", [30, 40, 60, 80])

    # Botão para processar
    if st.button("Gerar Cortes"):
        if not youtube_url:
            st.error("Por favor, insira um link válido do YouTube.")
            return
        
        with st.spinner("Baixando o vídeo..."):
            video_path = download_video(youtube_url)
        
        if video_path:
            st.success("Vídeo baixado com sucesso!")
            with st.spinner("Gerando cortes..."):
                clips = generate_clips(video_path, clip_length)
            
            if clips:
                st.success("Cortes gerados com sucesso!")
                st.write("Baixe os cortes abaixo:")
                for clip in clips:
                    clip_name = os.path.basename(clip)
                    with open(clip, "rb") as f:
                        st.download_button(
                            label=f"Baixar {clip_name}",
                            data=f,
                            file_name=clip_name,
                            mime="video/mp4"
                        )

if __name__ == "__main__":
    main()
