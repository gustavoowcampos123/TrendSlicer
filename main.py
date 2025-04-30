import os
import streamlit as st
from random import randint
import subprocess
import json
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import speech_recognition as sr
import random
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Função para conectar ao banco de dados SQLite
def connect_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, verified INTEGER)''')
    conn.commit()
    return conn

# Função para enviar o código de verificação por email
def send_verification_email(to_email, verification_code):
    sender_email = "seuemail@gmail.com"
    sender_password = "sua_senha"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    subject = "Código de Verificação"
    body = f"Seu código de verificação é: {verification_code}"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Usar TLS para segurança
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar o email: {e}")
        return False

# Função para registrar um usuário
def register_user(email, password):
    conn = connect_db()
    c = conn.cursor()
    verification_code = random.randint(100000, 999999)

    c.execute("INSERT INTO users (email, password, verified) VALUES (?, ?, ?)",
              (email, password, 0))
    conn.commit()
    conn.close()

    # Envia o código de verificação
    send_verification_email(email, verification_code)
    return verification_code

# Função para verificar o código
def verify_code(email, code):
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()

    if user and user[2] == 0:  # Verifica se o usuário não foi verificado
        stored_code = code
        if stored_code == user[2]:  # Se o código for correto
            c.execute("UPDATE users SET verified = 1 WHERE email=?", (email,))
            conn.commit()
            conn.close()
            return True
        conn.close()
    return False

# Função para obter a duração do vídeo
def get_video_duration(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as e:
        raise RuntimeError(f"Erro ao obter a duração do vídeo: {e}")

# Função para gerar cortes de vídeo
def generate_clips(video_path, clip_length, aspect_ratio, num_clips=10, output_path="cuts"):
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

            if aspect_ratio == "9:16":
                ffmpeg_command += ["-vf", "crop=in_h*9/16:in_h"]

            ffmpeg_command.append(output_file)

            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0 and is_video_valid(output_file):
                clips.append((output_file, start_time))
            else:
                st.warning(f"O clipe {i + 1} está corrompido e foi ignorado.")

            progress_bar.progress(int((i + 1) / num_clips * 100))

        return clips
    except Exception as e:
        st.error(f"Erro ao gerar os cortes: {e}")
        return None

# Função para transcrever o áudio com o Google
def transcribe_audio_with_google(audio_path):
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

# Função principal
def main():
    st.title("Gerador de Cortes Virais para YouTube")
    st.write("Insira um link de vídeo do YouTube e gere cortes curtos automaticamente!")

    menu = ["Login", "Cadastro"]
    choice = st.sidebar.selectbox("Escolha uma opção", menu)

    if choice == "Cadastro":
        st.subheader("Cadastro de Usuário")
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")

        if st.button("Cadastrar"):
            verification_code = register_user(email, password)
            st.success(f"Cadastro bem-sucedido. Enviamos um código para o seu email.")
            st.text(f"Seu código de verificação é: {verification_code}")

    elif choice == "Login":
        st.subheader("Login de Usuário")
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            conn = connect_db()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
            user = c.fetchone()

            if user:
                if user[2] == 1:
                    st.success("Login bem-sucedido!")
                    youtube_url = st.text_input("Link do vídeo do YouTube", "")
                    clip_length = st.selectbox("Escolha a duração dos cortes (em segundos)", [30, 40, 60, 80])
                    aspect_ratio = st.selectbox("Escolha a proporção dos cortes", ["16:9", "9:16"])

                    if st.button("Gerar Cortes"):
                        if not youtube_url:
                            st.error("Por favor, insira um link válido do YouTube.")
                            return

                        with st.spinner("Baixando o vídeo..."):
                            video_path, _ = download_video(youtube_url)

                        if video_path:
                            st.success("Vídeo baixado com sucesso!")
                            with st.spinner("Gerando cortes..."):
                                clips = generate_clips(video_path, clip_length, aspect_ratio)
                                if clips:
                                    st.session_state["clips"] = clips
                                    st.success("Cortes gerados com sucesso!")
                                else:
                                    st.error("Erro ao gerar os cortes.")
                else:
                    st.warning("Email não verificado. Verifique sua caixa de entrada para o código.")
            else:
                st.error("Email ou senha incorretos.")
            conn.close()

if __name__ == "__main__":
    main()
