import re
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from a_selenium2df import get_df
from PrettyColorPrinter import add_printer
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import numpy as np

add_printer(1)

# Função para obter DataFrame de uma página
def obter_dataframe(driver, query="*"):
    df = pd.DataFrame()
    while df.empty:
        df = get_df(
            driver,
            By,
            WebDriverWait,
            expected_conditions,
            queryselector=query,
            with_methods=True,
        )
    return df

# Função para processar uma URL e retornar DataFrame de jogos
def process_url(url):
    driver = Driver(uc=True)
    driver.get(url)
    try:
        df = obter_dataframe(driver, query='ms-event')
        df = df.dropna(subset='aa_innerText').aa_innerText.apply(
            lambda x: pd.Series([q for q in re.split(r'[\n\r]', x) if not re.match(r'^\d+$', q)])
        )[[2, 0, 1, 4, 5, 6]].rename(
            columns={0: 'team1_nome', 1: 'team2_nome', 2: 'data', 4: 'team1', 5: 'empate', 6: 'team2'}
        ).dropna().assign(
            team1=lambda q: q.team1.str.replace(',', '.'),
            team2=lambda q: q.team2.str.replace(',', '.'),
            empate=lambda q: q.empate.str.replace(',', '.')
        ).astype(
            {'team1': 'Float64', 'empate': 'Float64', 'team2': 'Float64'}
        )
        driver.quit()
        return df
    except Exception as e:
        print(e)
        driver.quit()
        return pd.DataFrame()

# Função para enviar email com imagem anexada
def send_email_with_image(subject, body, to_email, image_path):
    from_email = "...@hotmail.com"  # seu email hotmail
    from_password = "..."  # sua senha hotmail

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with open(image_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {image_path}",
        )
        msg.attach(part)

    server = smtplib.SMTP('smtp.office365.com', 587)
    server.starttls()
    server.login(from_email, from_password)
    text = msg.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()

# Função para criar uma imagem da tabela com cores personalizadas
def create_image_from_table(dataframe, image_path):
    # Configurar a figura e o eixo
    fig, ax = plt.subplots(figsize=(15, dataframe.shape[0] * 0.5))
    ax.axis('tight')
    ax.axis('off')

    # Configurar as cores das células e o fundo preto
    cell_colors = []
    text_colors = []
    for i in range(len(dataframe)):
        row_colors = []
        row_text_colors = []
        for j in range(len(dataframe.columns)):
            row_colors.append('black')  # Fundo preto para todas as células
            if dataframe.columns[j] == 'team1':
                row_text_colors.append('yellow')  # Odds do team1 em amarelo
            elif dataframe.columns[j] == 'team2':
                row_text_colors.append('green')  # Odds do team2 em verde
            elif dataframe.columns[j] == 'empate':
                row_text_colors.append('red')  # Odds do empate em vermelho
            elif dataframe.columns[j] == 'data':
                row_text_colors.append('cyan')  # Data em ciano
            else:
                row_text_colors.append('white')  # Texto padrão em branco
        cell_colors.append(row_colors)
        text_colors.append(row_text_colors)
    
    # Adicionar a tabela à figura
    table = ax.table(
        cellText=dataframe.values,
        colLabels=dataframe.columns,
        cellLoc='center',
        loc='center',
        cellColours=cell_colors
    )

    # Estilizar a tabela
    for key, cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        cell.set_linewidth(0.5)
        if key[0] == 0:  # Células de título
            cell.set_facecolor('black')
            cell.set_text_props(weight='bold', color='white')
        else:
            cell.set_text_props(color=text_colors[key[0]-1][key[1]])

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.2)
    
    # Salvar a imagem
    plt.savefig(image_path, bbox_inches='tight', dpi=300, facecolor='#000000')

# Lista de URLs
urls = [
    "https://sports.sportingbet.com/pt-br/sports/futebol-4"
    # Adicione mais URLs aqui
]

# Extração de dados usando ThreadPoolExecutor
all_dataframes = []
with ThreadPoolExecutor(max_workers=5) as executor:
    future_to_url = {executor.submit(process_url, url): url for url in urls}
    for future in as_completed(future_to_url):
        url = future_to_url[future]
        try:
            data = future.result()
            all_dataframes.append(data)
        except Exception as exc:
            print(f"{url} generated an exception: {exc}")

# Combinar todos os DataFrames em um só
final_df = pd.concat(all_dataframes).reset_index(drop=True)

# Caminho do arquivo da imagem
image_path = "table_image.png"

# Criar imagem da tabela
create_image_from_table(final_df, image_path)

# Enviar o email com a imagem anexada
send_email_with_image(
    subject="Dados dos Jogos de Futebol",
    body="Por favor, encontre em anexo os dados dos jogos de futebol.",
    to_email="...@gmail.com",  # Email de destino podendo ser gmail ou hotmail
    image_path=image_path
)

# Imprimir o DataFrame para verificação
print(final_df)