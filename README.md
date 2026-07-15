# API для управления личными подписками и регулярными платежами

### Как развернуть проект:
1. Клонируйте репозиторий через Git
cd <ваша директория, в которую вы хотите разместить проект>
git clone <SSH-ключ данного репозитория>
2. Устанавливаем uv
**Windows:**
```bash
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**MacOS и Linux:**
```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
```
3. Запускаем поочередно команды:
```bash
   uv sync --all-groups
```