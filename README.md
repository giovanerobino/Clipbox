# Clipbox

App desktop em Python para recortar qualquer região da tela (`Ctrl+T`), copiar a imagem e o texto reconhecido, detectar o idioma, traduzir e ler em voz alta.

## O que faz

1. **Ctrl+T** abre uma overlay. Arraste uma box em torno de imagem, vídeo ou página.
2. A **imagem** vai para o clipboard. O **texto OCR** também é colocado no clipboard no mesmo instante, para colar num `.txt`.
3. O idioma do texto é **detectado**. Você escolhe o destino (ex.: inglês → português) e traduz.
4. **Ler texto bruto** ou **Ler tradução** usa as vozes do Windows.

## Requisitos

- Windows 10/11
- Python 3.11+ (testado com 3.13)

## Instalação

```powershell
cd clipbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

O app fica na bandeja do sistema. `Esc` cancela o recorte.

No Windows você também pode dar dois cliques em `run.bat`.

## Testes

```powershell
pytest -q
```

A tradução usa o Google Translate (precisa de internet na primeira execução). O OCR baixa modelos ONNX na primeira leitura.
