(() => {
  const el = {
    generationMode: document.getElementById("generationMode"),
    videoInputsBlock: document.getElementById("videoInputsBlock"),
    sidanceInputsBlock: document.getElementById("sidanceInputsBlock"),
    videoInput: document.getElementById("videoInput"),
    imageInput: document.getElementById("imageInput"),
    audioInput: document.getElementById("audioInput"),
    overlayText: document.getElementById("overlayText"),
    textPosition: document.getElementById("textPosition"),
    textSize: document.getElementById("textSize"),
    textColor: document.getElementById("textColor"),
    imageDuration: document.getElementById("imageDuration"),
    sidanceSize: document.getElementById("sidanceSize"),
    sidanceSteps: document.getElementById("sidanceSteps"),
    sidanceGuidance: document.getElementById("sidanceGuidance"),
    sidanceSeed: document.getElementById("sidanceSeed"),
    promptInput: document.getElementById("promptInput"),
    generateBtn: document.getElementById("generateBtn"),
    setupBox: document.getElementById("setupBox"),
    statusBox: document.getElementById("statusBox"),
    chatMessages: document.getElementById("chatMessages"),
    chatInput: document.getElementById("chatInput"),
    sendChatBtn: document.getElementById("sendChatBtn"),
    markerList: document.getElementById("markerList"),
    clearMarkersBtn: document.getElementById("clearMarkersBtn"),
    exportMarkersBtn: document.getElementById("exportMarkersBtn"),
    toggleMarkModeBtn: document.getElementById("toggleMarkModeBtn"),
    previewVideo: document.getElementById("previewVideo"),
    overlayCanvas: document.getElementById("overlayCanvas"),
    timeLabel: document.getElementById("timeLabel"),
    videoStage: document.getElementById("videoStage"),
  };

  const state = {
    markers: [],
    markerSeq: 1,
    chatHistory: [],
    outputVideoPath: "",
    markModeEnabled: false,
    dragging: null,
    draggingCurrent: null,
  };

  const ctx = el.overlayCanvas.getContext("2d");

  function setStatus(text, isError = false) {
    el.statusBox.textContent = text;
    el.statusBox.style.borderLeftColor = isError ? "#b42318" : "#0f7a46";
    el.statusBox.style.background = isError ? "#feeceb" : "#e7f6ee";
  }

  function setSetupStatus(text, isWarning = true) {
    el.setupBox.textContent = text;
    if (isWarning) {
      el.setupBox.style.borderLeftColor = "#bd7400";
      el.setupBox.style.background = "#fff5e8";
      return;
    }
    el.setupBox.style.borderLeftColor = "#0f7a46";
    el.setupBox.style.background = "#e7f6ee";
  }

  function getGenerationMode() {
    return el.generationMode.value === "sidance_local" ? "sidance_local" : "video_ia";
  }

  function toggleGenerationModeUi() {
    const mode = getGenerationMode();
    const sidanceMode = mode === "sidance_local";

    el.videoInputsBlock.classList.toggle("hidden-block", sidanceMode);
    el.sidanceInputsBlock.classList.toggle("hidden-block", !sidanceMode);
    el.generateBtn.textContent = sidanceMode ? "Generar vídeo SIDANCE local" : "Generar vídeo";

    if (sidanceMode) {
      setStatus("Modo SIDANCE local activo. Solo necesitas texto de instrucción.");
      return;
    }
    setStatus("Modo VIDEO IA activo. Usa vídeo o imagen, más audio, texto y prompt.");
  }

  function formatTime(sec) {
    const value = Math.max(0, Math.floor(Number(sec) || 0));
    const mm = Math.floor(value / 60);
    const ss = value % 60;
    return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  }

  function addChatMessage(role, text) {
    const safeText = String(text || "").trim();
    if (!safeText) {
      return;
    }

    const box = document.createElement("div");
    box.className = `msg ${role}`;
    box.textContent = safeText;
    el.chatMessages.appendChild(box);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
    state.chatHistory.push({ role, content: safeText });
  }

  function updateMarkModeUi() {
    if (state.markModeEnabled) {
      el.toggleMarkModeBtn.textContent = "Modo marcar: ON";
      el.toggleMarkModeBtn.classList.remove("off");
      el.toggleMarkModeBtn.classList.add("on");
      el.overlayCanvas.classList.add("mark-enabled");
      return;
    }

    el.toggleMarkModeBtn.textContent = "Modo marcar: OFF";
    el.toggleMarkModeBtn.classList.remove("on");
    el.toggleMarkModeBtn.classList.add("off");
    el.overlayCanvas.classList.remove("mark-enabled");
  }

  function getVideoBoxPixels() {
    const cw = el.overlayCanvas.width;
    const ch = el.overlayCanvas.height;
    const vw = el.previewVideo.videoWidth || cw;
    const vh = el.previewVideo.videoHeight || ch;

    const scale = Math.min(cw / vw, ch / vh);
    const width = vw * scale;
    const height = vh * scale;
    const left = (cw - width) / 2;
    const top = (ch - height) / 2;

    return { left, top, width, height };
  }

  function normalizeEventPosition(event) {
    const rect = el.overlayCanvas.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * el.overlayCanvas.width;
    const py = ((event.clientY - rect.top) / rect.height) * el.overlayCanvas.height;

    const box = getVideoBoxPixels();
    if (px < box.left || px > box.left + box.width || py < box.top || py > box.top + box.height) {
      return null;
    }

    const x = ((px - box.left) / box.width) * 100;
    const y = ((py - box.top) / box.height) * 100;
    return { x, y };
  }

  function percentToPixel(point) {
    const box = getVideoBoxPixels();
    return {
      x: box.left + (point.x / 100) * box.width,
      y: box.top + (point.y / 100) * box.height,
      w: (point.w / 100) * box.width,
      h: (point.h / 100) * box.height,
    };
  }

  function resizeCanvas() {
    const rect = el.videoStage.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    el.overlayCanvas.width = Math.max(1, Math.floor(rect.width * dpr));
    el.overlayCanvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawOverlay();
  }

  function drawMarker(marker, isActive) {
    const px = percentToPixel(marker);
    const color = isActive ? "#ffd43b" : "#56b4ff";

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = isActive ? 2.8 : 2;

    if (marker.type === "box" && marker.w > 0.5 && marker.h > 0.5) {
      ctx.strokeRect(px.x, px.y, px.w, px.h);
      ctx.fillRect(px.x + 1, px.y + 1, 2, 2);
      ctx.fillText(`#${marker.id}`, px.x + 6, Math.max(14, px.y - 6));
      return;
    }

    const radius = isActive ? 7 : 5;
    ctx.beginPath();
    ctx.arc(px.x, px.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillText(`#${marker.id}`, px.x + 9, px.y - 7);
  }

  function drawOverlay() {
    const width = el.overlayCanvas.width;
    const height = el.overlayCanvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.font = "12px Segoe UI";

    const now = Number(el.previewVideo.currentTime || 0);
    for (const marker of state.markers) {
      const active = Math.abs(now - marker.time) < 0.45;
      drawMarker(marker, active);
    }

    if (state.dragging && state.draggingCurrent) {
      const start = percentToPixel({
        x: state.dragging.x,
        y: state.dragging.y,
        w: 0,
        h: 0,
      });
      const end = percentToPixel({
        x: state.draggingCurrent.x,
        y: state.draggingCurrent.y,
        w: 0,
        h: 0,
      });

      const left = Math.min(start.x, end.x);
      const top = Math.min(start.y, end.y);
      const w = Math.abs(end.x - start.x);
      const h = Math.abs(end.y - start.y);

      ctx.save();
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = "#ff8b2c";
      ctx.lineWidth = 2;
      ctx.strokeRect(left, top, w, h);
      ctx.restore();
    }
  }

  function renderMarkers() {
    el.markerList.innerHTML = "";

    if (!state.markers.length) {
      const empty = document.createElement("li");
      empty.className = "marker-item";
      empty.textContent = "Sin marcas aún.";
      el.markerList.appendChild(empty);
      return;
    }

    for (const marker of state.markers) {
      const item = document.createElement("li");
      item.className = "marker-item";

      const note = marker.note ? ` | nota: ${marker.note}` : "";
      item.textContent =
        `#${marker.id} | t=${formatTime(marker.time)} | x=${marker.x.toFixed(1)}% y=${marker.y.toFixed(1)}%` +
        `${marker.type === "box" ? ` | w=${marker.w.toFixed(1)} h=${marker.h.toFixed(1)}` : ""}${note}`;

      const actions = document.createElement("div");
      actions.className = "marker-actions";

      const goBtn = document.createElement("button");
      goBtn.textContent = "Ir";
      goBtn.addEventListener("click", () => {
        el.previewVideo.currentTime = marker.time;
        el.previewVideo.play();
      });

      const delBtn = document.createElement("button");
      delBtn.textContent = "Borrar";
      delBtn.addEventListener("click", () => {
        state.markers = state.markers.filter((m) => m.id !== marker.id);
        renderMarkers();
        drawOverlay();
      });

      actions.appendChild(goBtn);
      actions.appendChild(delBtn);
      item.appendChild(actions);
      el.markerList.appendChild(item);
    }
  }

  function createMarkerFromDrag(start, end, timeSec) {
    const minX = Math.max(0, Math.min(start.x, end.x));
    const minY = Math.max(0, Math.min(start.y, end.y));
    const maxX = Math.min(100, Math.max(start.x, end.x));
    const maxY = Math.min(100, Math.max(start.y, end.y));
    const w = Math.max(0, maxX - minX);
    const h = Math.max(0, maxY - minY);

    const markerType = w > 1.2 || h > 1.2 ? "box" : "point";
    const note = window.prompt("Nota de la marca (opcional):", "") || "";

    const marker = {
      id: state.markerSeq++,
      type: markerType,
      time: Number(timeSec.toFixed(3)),
      x: Number((markerType === "box" ? minX : maxX).toFixed(2)),
      y: Number((markerType === "box" ? minY : maxY).toFixed(2)),
      w: Number((markerType === "box" ? w : 0).toFixed(2)),
      h: Number((markerType === "box" ? h : 0).toFixed(2)),
      note: note.trim(),
    };

    state.markers.push(marker);
    renderMarkers();
    drawOverlay();
    setStatus(`Marca #${marker.id} creada en ${formatTime(marker.time)}.`);
  }

  async function generateVideo() {
    const mode = getGenerationMode();
    const videoFile = el.videoInput.files[0];
    const imageFile = el.imageInput.files[0];
    const audioFile = el.audioInput.files[0];
    const prompt = el.promptInput.value.trim();

    if (!prompt) {
      setStatus("Falta escribir el texto de instrucción.", true);
      return;
    }

    if (mode === "video_ia" && !videoFile) {
      if (!imageFile) {
        setStatus("Falta elegir vídeo o imagen.", true);
        return;
      }
    }

    if (mode === "video_ia" && !videoFile && imageFile) {
      setStatus("Generaremos vídeo base desde imagen y aplicaremos tu instrucción.");
    }

    el.generateBtn.disabled = true;
    setStatus("Generando vídeo... espera un momento.");

    try {
      let res;
      if (mode === "sidance_local") {
        const payload = {
          prompt,
          size_label: String(el.sidanceSize.value || "").trim(),
          num_inference_steps: Number(el.sidanceSteps.value || 28),
          guidance_scale: Number(el.sidanceGuidance.value || 6),
          seed: Number(el.sidanceSeed.value || -1),
        };
        res = await fetch("/api/generate-sidance", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
      } else {
        const body = new FormData();
        body.append("video", videoFile);
        if (imageFile) {
          body.append("image", imageFile);
        }
        if (audioFile) {
          body.append("audio", audioFile);
        }
        body.append("prompt", prompt);
        body.append("overlay_text", String(el.overlayText.value || ""));
        body.append("text_position", String(el.textPosition.value || "abajo"));
        body.append("text_size", String(el.textSize.value || "46"));
        body.append("text_color", String(el.textColor.value || "blanco"));
        body.append("image_duration_seconds", String(el.imageDuration.value || "8"));
        res = await fetch("/api/generate", {
          method: "POST",
          body,
        });
      }

      const data = await res.json();

      if (!res.ok || !data.ok) {
        setStatus(data.message || "Error generando vídeo.", true);
        return;
      }

      state.outputVideoPath = data.output_video_path || "";
      state.markers = [];
      state.markerSeq = 1;
      renderMarkers();

      if (!data.output_video_url) {
        setStatus(data.message || "No se recibió vídeo de salida.", true);
        return;
      }

      const source = `${data.output_video_url}?ts=${Date.now()}`;
      el.previewVideo.src = source;
      el.previewVideo.load();
      addChatMessage(
        "assistant",
        "Vídeo listo. Ya puedes conversar conmigo y crear marcas sobre la vista previa."
      );
      const backendText = data.backend ? `Motor usado: ${data.backend}.` : "";
      const modelText = data.model_id ? `Modelo: ${data.model_id}.` : "";
      setStatus(`${data.message || "Vídeo generado."}\n${backendText}\n${modelText}`.trim());
    } catch (err) {
      setStatus(`Fallo de red o local: ${String(err)}`, true);
    } finally {
      el.generateBtn.disabled = false;
    }
  }

  async function sendChat() {
    const message = el.chatInput.value.trim();
    if (!message) {
      return;
    }

    addChatMessage("user", message);
    el.chatInput.value = "";
    el.sendChatBtn.disabled = true;
    let timeoutRef = null;
    const controller = new AbortController();

    try {
      timeoutRef = window.setTimeout(() => controller.abort(), 25000);
      const res = await fetch("/api/chat", {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          markers: state.markers,
          current_time: Number(el.previewVideo.currentTime || 0),
          chat_history: state.chatHistory,
          output_video_path: state.outputVideoPath,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        addChatMessage("assistant", data.message || "No pude responder ahora.");
        return;
      }
      addChatMessage("assistant", data.reply || "Sin respuesta.");
    } catch (err) {
      if (String(err).toLowerCase().includes("abort")) {
        addChatMessage("assistant", "El chat tardó demasiado. Intenta enviar de nuevo.");
      } else {
        addChatMessage("assistant", `Error de chat: ${String(err)}`);
      }
    } finally {
      if (timeoutRef) {
        window.clearTimeout(timeoutRef);
      }
      el.sendChatBtn.disabled = false;
    }
  }

  function exportMarkersAsJson() {
    const payload = {
      exported_at: new Date().toISOString(),
      output_video_path: state.outputVideoPath,
      markers: state.markers,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `marcas_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function bindEvents() {
    el.generationMode.addEventListener("change", () => {
      toggleGenerationModeUi();
    });
    el.generateBtn.addEventListener("click", generateVideo);
    el.sendChatBtn.addEventListener("click", sendChat);
    el.toggleMarkModeBtn.addEventListener("click", () => {
      state.markModeEnabled = !state.markModeEnabled;
      updateMarkModeUi();
      if (state.markModeEnabled) {
        setStatus("Modo marcar activado. Haz clic o arrastra sobre el vídeo.");
      } else {
        setStatus("Modo marcar desactivado. Ya puedes usar play y la barra del vídeo.");
      }
    });
    el.clearMarkersBtn.addEventListener("click", () => {
      state.markers = [];
      renderMarkers();
      drawOverlay();
      setStatus("Marcas eliminadas.");
    });
    el.exportMarkersBtn.addEventListener("click", exportMarkersAsJson);

    el.chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChat();
      }
    });

    el.previewVideo.addEventListener("timeupdate", () => {
      el.timeLabel.textContent = `Tiempo: ${formatTime(el.previewVideo.currentTime)}`;
      drawOverlay();
    });
    el.previewVideo.addEventListener("seeked", drawOverlay);
    el.previewVideo.addEventListener("loadedmetadata", () => {
      resizeCanvas();
      drawOverlay();
    });

    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("orientationchange", resizeCanvas);

    el.overlayCanvas.addEventListener("mousedown", (event) => {
      if (!state.markModeEnabled) {
        return;
      }
      if (!el.previewVideo.src) {
        setStatus("Primero genera un vídeo para poder marcar.", true);
        return;
      }
      const point = normalizeEventPosition(event);
      if (!point) {
        return;
      }
      state.dragging = {
        x: point.x,
        y: point.y,
        time: Number(el.previewVideo.currentTime || 0),
      };
      state.draggingCurrent = { x: point.x, y: point.y };
      drawOverlay();
    });

    el.overlayCanvas.addEventListener("mousemove", (event) => {
      if (!state.markModeEnabled) {
        return;
      }
      if (!state.dragging) {
        return;
      }
      const point = normalizeEventPosition(event);
      if (!point) {
        return;
      }
      state.draggingCurrent = { x: point.x, y: point.y };
      drawOverlay();
    });

    el.overlayCanvas.addEventListener("mouseup", (event) => {
      if (!state.markModeEnabled) {
        return;
      }
      if (!state.dragging) {
        return;
      }

      const end = normalizeEventPosition(event) || state.draggingCurrent || state.dragging;
      const start = state.dragging;
      state.dragging = null;
      state.draggingCurrent = null;

      createMarkerFromDrag(start, end, start.time);
    });

    el.overlayCanvas.addEventListener("mouseleave", () => {
      if (!state.markModeEnabled) {
        return;
      }
      if (!state.dragging) {
        return;
      }
      state.draggingCurrent = null;
      drawOverlay();
    });
  }

  async function loadSystemStatus() {
    try {
      const res = await fetch("/api/system-status");
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setSetupStatus("No se pudo leer estado del sistema.", true);
        return;
      }

      const sidance = data.sidance || {};
      const sidanceReady = Boolean(sidance.available);
      const sidanceModel = sidance.model_id ? ` (${sidance.model_id})` : "";
      const sidanceLine = sidanceReady
        ? `SIDANCE local listo${sidanceModel}.`
        : `SIDANCE local no disponible: ${sidance.message || "revisa GPU/dependencias"}.`;

      const backendLine =
        data.effective_backend === "runway"
          ? "Modo nube activo: Runway."
          : "Modo local activo (sin cuentas).";

      const extraLine =
        data.effective_backend === "runway"
          ? "Si Runway falla, la aplicación usa local como respaldo."
          : "Para activar nube después: añade RUNWAY_API_KEY en .env.";

      const warning = !sidanceReady;
      setSetupStatus(
        `${backendLine}\nFormato fijo VIDEO IA: ${data.output_format}.\n${sidanceLine}\n${extraLine}`,
        warning
      );
    } catch (err) {
      setSetupStatus(`Estado no disponible: ${String(err)}`, true);
    }
  }

  function init() {
    bindEvents();
    renderMarkers();
    updateMarkModeUi();
    toggleGenerationModeUi();
    resizeCanvas();
    loadSystemStatus();
    addChatMessage(
      "assistant",
      "Hola. Puedes usar VIDEO IA (editar) o SIDANCE local (texto a vídeo)."
    );
  }

  init();
})();
