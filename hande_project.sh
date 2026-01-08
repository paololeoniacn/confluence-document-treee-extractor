#!/bin/bash
# =============================================================================
# Confluence Downloader Stack Manager (conf-get-pages)
# =============================================================================
# Gestisce il ciclo di vita del container per l'export ricorsivo di Confluence
# =============================================================================

set -e

# --- Configurazione ---
PROJECT_NAME="conf-get-pages"
IMAGE_NAME="localhost/${PROJECT_NAME}"
CONTAINER_NAME="${PROJECT_NAME}-container"
NETWORK_NAME="${PROJECT_NAME}-net"
ENV_FILE=".env"

# --- Colori ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Helper Functions ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# --- Comandi ---

cmd_status() {
    echo -e "\n${CYAN}=== RIEPILOGO RISORSE: ${PROJECT_NAME} ===${NC}"
    
    # Check Container
    if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        local c_status=$(podman inspect ${CONTAINER_NAME} --format '{{.State.Status}}')
        echo -e "Container [${CONTAINER_NAME}]: ${GREEN}PRESENTE${NC} (Stato: $c_status)"
    else
        echo -e "Container [${CONTAINER_NAME}]: ${RED}ASSENTE${NC}"
    fi

    # Check Image
    if podman image exists "${IMAGE_NAME}"; then
        echo -e "Immagine  [${IMAGE_NAME}]: ${GREEN}PRESENTE${NC}"
    else
        echo -e "Immagine  [${IMAGE_NAME}]: ${RED}ASSENTE${NC}"
    fi

    # Check Network
    if podman network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        echo -e "Network   [${NETWORK_NAME}]: ${GREEN}PRESENTE${NC}"
    else
        echo -e "Network   [${NETWORK_NAME}]: ${RED}ASSENTE${NC}"
    fi
    echo -e "${CYAN}==========================================${NC}\n"
}

check_podman() {
    log_info "Verifica requisiti di sistema..."
    
    # 1. Verifica se il binario esiste
    if ! command -v podman &> /dev/null; then
        log_error "Podman non è installato. Installa Podman per continuare."
        exit 1
    fi

    # 2. Se su Mac o Windows, verifica se la macchina è attiva
    if [[ "$(uname)" == "Darwin" ]] || [[ "$(expr substr $(uname -s) 1 5)" == "MINGW" ]]; then
        if ! podman machine inspect &> /dev/null; then
            log_warn "Podman machine non inizializzata. Eseguo: podman machine init"
            podman machine init
        fi
        
        if ! podman machine list | grep -q "Currently running"; then
            log_warn "Podman machine ferma. Avvio in corso..."
            podman machine start
        fi
    fi
    log_success "Podman è pronto."
}

cmd_shell() {
    check_podman
    log_info "Apertura shell interattiva nel container di debug..."
    
    # Avvia un container temporaneo con le stesse env e volumi
    # Usiamo 'sh' perché le immagini slim spesso non hanno 'bash'
    podman run -it --rm \
        --name "${PROJECT_NAME}-debug" \
        --env-file "$ENV_FILE" \
        --dns 8.8.8.8 \
        -v ./output:/app/downloaded_pages:Z \
        --entrypoint /bin/sh \
        "${IMAGE_NAME}:latest"
}

cmd_clean() {
    local level="${1:-all}"
    log_info "=== INIZIO PROCEDURA DI PULIZIA (Livello richiesto: $level) ==="

    # --- FASE 1: CONTAINER ---
    log_info "[FASE 1/4] Verifica Container..."
    if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        log_warn "  -> Trovato container '${CONTAINER_NAME}'. Rimozione in corso..."
        podman rm -f "${CONTAINER_NAME}" >/dev/null
        log_success "  -> Container rimosso."
    else
        echo "  -> Nessun container trovato. Skip."
    fi

    # --- FASE 2: IMMAGINI ---
    log_info "[FASE 2/4] Verifica Immagini..."
    if [[ "$level" == "all" ]]; then
        if podman image exists "${IMAGE_NAME}"; then
            log_warn "  -> Trovata immagine '${IMAGE_NAME}'. Rimozione in corso..."
            podman rmi -f "${IMAGE_NAME}:latest" >/dev/null
            log_success "  -> Immagine rimossa."
        else
            echo "  -> Nessuna immagine trovata. Skip."
        fi
    else
        echo "  -> Livello '$level': conservazione immagini."
    fi

    # --- FASE 3: NETWORK ---
    log_info "[FASE 3/4] Verifica Network..."
    if [[ "$level" == "all" ]]; then
        if podman network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
            log_warn "  -> Trovata network '${NETWORK_NAME}'. Rimozione in corso..."
            podman network rm "${NETWORK_NAME}" >/dev/null
            log_success "  -> Network rimossa."
        else
            echo "  -> Nessuna network trovata. Skip."
        fi
    else
        echo "  -> Livello '$level': conservazione network."
    fi

    # --- FASE 4: OUTPUT ---
    log_info "[FASE 4/4] Verifica Dati Output..."
    if [[ "$level" == "all" || "$level" == "outputs" ]]; then
        if [ -d "./output" ] && [ "$(ls -A ./output 2>/dev/null)" ]; then
            log_warn "  -> Svuotamento cartella ./output..."
            rm -rf ./output/*
            log_success "  -> Dati rimossi."
        else
            echo "  -> Cartella output già vuota o inesistente. Skip."
        fi
    else
        echo "  -> Livello '$level': conservazione dati scaricati."
    fi

    log_success "=== PROCEDURA DI PULIZIA TERMINATA ==="
    cmd_status
}

cmd_build() {
    log_info "Costruzione dell'immagine '${IMAGE_NAME}'..."
    podman build -t "${IMAGE_NAME}:latest" .
    log_success "Immagine costruita."
}

validate_env() {
    log_info "Validazione configurazione .env..."
    if [ ! -f "$ENV_FILE" ]; then
        log_error "File $ENV_FILE non trovato!"
        exit 1
    fi

    # Controllo che le chiavi non siano vuote
    local required_vars=("CONFLUENCE_URL" "SPACE_KEY" "CONFLUENCE_USER" "CONFLUENCE_TOKEN" "PARENT_PAGE_ID")
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=$" "$ENV_FILE"; then
            log_error "La variabile $var è mancante o vuota nel file $ENV_FILE"
            exit 1
        fi
    done
    log_success "Configurazione valida."
}

cmd_start() {
    validate_env

    if ! podman image exists "${IMAGE_NAME}"; then
        log_warn "Immagine non trovata localmente. Avvio build..."
        cmd_build
    fi

    mkdir -p ./output
    
    log_info "Avvio container per il download..."
    # --env-file inietta le variabili direttamente nel container
    podman run -it --rm \
        --name "${CONTAINER_NAME}" \
        --env-file "$ENV_FILE" \
        -v ./output:/app/downloaded_pages:Z \
        "${IMAGE_NAME}:latest"
    
    log_success "Esecuzione completata. I file sono in ./output"
}

# --- Main Switch ---
case "$1" in
    build)      cmd_build ;;
    shell|sh)   cmd_shell ;;
    start|up)   cmd_start ;;
    status|ps)  cmd_status ;;
    clean|rm)   cmd_clean "$2" ;;
    restart)    cmd_clean all && cmd_start ;;
    logs)       podman logs -f "${CONTAINER_NAME}" ;;
    *)
        echo -e "${CYAN}--- Confluence Downloader CLI ---${NC}"
        echo "Usage: $0 {build|start|status|clean [containers|all|outputs]|restart|logs}"
        exit 1
esac