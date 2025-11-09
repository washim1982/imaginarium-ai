import React, { useEffect, useRef, useState } from "react";
import { FiPlus, FiMic } from "react-icons/fi";
import { useApi } from "../services/api";
import MarkdownMessage from "../components/MarkdownMessage";
import WeatherCard from "../components/WeatherCard";

const GREETING_PHRASES = [
  "How can I help you today?",
  "What's on your mind?",
  "Ask me anything—I'm listening.",
  "Ready when you are. Just start typing.",
];

export default function ModelHub() {
  const api = useApi();
  const [models, setModels] = useState([]);
  const [selected, setSelected] = useState(["granite4:tiny-h"]);
  const [messages, setMessages] = useState([]);
  const chatWindowRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const dropdownRef = useRef(null);
  const [attachments, setAttachments] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [greetingIndex, setGreetingIndex] = useState(0);
  const [modelListOpen, setModelListOpen] = useState(false);
  const [weatherUnits, setWeatherUnits] = useState(
    () => window.localStorage.getItem("weatherUnits") || "metric"
  );

  // Load models
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/models");
        setModels(data.models || []);
      } catch (err) {
        console.error("Error loading models:", err);
      }
    })();
  }, [api]);


  const appendToPrompt = (chunk) => {
    if (!chunk) return;
    setPrompt((prev) => {
      const base = prev.trimEnd();
      return base ? `${base}\n${chunk}` : chunk;
    });
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const readers = files.map(
      (file) =>
        new Promise((resolve) => {
          if (!file.type.startsWith("text") && file.type !== "application/json") {
            resolve({
              name: file.name,
              content: `[${file.name}] Selected (preview unavailable)`,
            });
            return;
          }
          const reader = new FileReader();
          reader.onload = () => {
            resolve({ name: file.name, content: reader.result });
          };
          reader.onerror = () => resolve({ name: file.name, content: "" });
          reader.readAsText(file);
        })
    );

    const contents = await Promise.all(readers);
    contents.forEach(({ name, content }) => {
      const snippet = content
        ? `[File: ${name}]\n${content.slice(0, 4000)}`
        : `[File: ${name}]`;
      appendToPrompt(snippet);
    });

    setAttachments(files.map((f) => f.name));
    event.target.value = "";
  };

  const toggleRecording = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Speech recognition not supported in this browser.");
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        appendToPrompt(transcript);
      };
      recognition.onend = () => setIsRecording(false);
      recognition.onerror = () => setIsRecording(false);
      recognitionRef.current = recognition;
    }

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      setIsRecording(true);
      recognitionRef.current.start();
    }
  };

  const send = async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || !selected[0]) return;

    const model = selected[0];
    setPrompt("");
    setAttachments([]);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmedPrompt },
      { role: "assistant", content: "", model },
    ]);

    try {
      const res = await fetch(`/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: api.defaults.headers.common.Authorization,
        },
        body: JSON.stringify({
          models: [model],
          prompt: trimmedPrompt,
          options: { weatherUnits },
        }),
      });

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value).trim();
        if (!chunk) continue;
        for (const line of chunk.split("\n")) {
          try {
            const j = JSON.parse(line);
            if (j.type === "weather" && j.weather) {
              setMessages((prev) => {
                const updated = [...prev];
                const lastIndex = updated.length - 1;
                if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
                  // Preserve any preceding assistant text (e.g., "Using location: …")
                  updated[lastIndex] = { ...updated[lastIndex], weather: j.weather };
                }
                return updated;
              });
            } else if (j.response) {
              fullText += j.response;
              setMessages((prev) => {
                const updated = [...prev];
                const lastIndex = updated.length - 1;
                if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
                  updated[lastIndex] = { ...updated[lastIndex], content: fullText };
                }
                return updated;
              });
            }
          } catch {
            continue;
          }
        }
      }
    } catch (err) {
      console.error("Error sending message:", err);
      setMessages((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
          updated[lastIndex] = {
            ...updated[lastIndex],
            content: "Error generating response. Please try again.",
          };
        }
        return updated;
      });
    }
  };

  const hasActivity =
    messages.length > 0 || prompt.trim().length > 0 || attachments.length > 0;

  useEffect(() => {
    const el = chatWindowRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (hasActivity) return;
    const id = setInterval(() => {
      setGreetingIndex((idx) => (idx + 1) % GREETING_PHRASES.length);
    }, 2800);
    return () => clearInterval(id);
  }, [hasActivity]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!dropdownRef.current) return;
      if (!dropdownRef.current.contains(event.target)) {
        setModelListOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={`modelhub`}>
      <div className={`chat-shell ${hasActivity ? "has-activity" : "idle"}`}>
        {!hasActivity && (
          <div className="greeting-hero">
            <div className="greeting-title">
              {GREETING_PHRASES[greetingIndex]}
            </div>
            <div className="greeting-subtitle">
              Type a prompt, attach a file, or speak a request to explore ideas.
            </div>
          </div>
        )}
        <div className="chat-window" ref={chatWindowRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="bubble">
                {m.role === "assistant" && m.weather ? (
                  <WeatherCard data={m.weather} />
                ) : m.role === "assistant" && !m.content ? (
                  <div className="thinking-indicator">
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                    <span className="thinking-text">Thinking…</span>
                  </div>
                ) : (
                  <MarkdownMessage text={m.content || ""} />
                )}
              </div>
            </div>
          ))}
        </div>

        <div className={`chat-composer ${hasActivity ? "" : "centered"}`}>
          <div className="composer-left">
            <div className="prompt-row">
              <div className="prompt-wrapper">
                <div className="input-icons">
                  <button
                    type="button"
                    className="input-icon"
                    aria-label="Attach files"
                    onClick={handleFileClick}
                  >
                    <FiPlus />
                  </button>
                  <button
                    type="button"
                    className={`input-icon ${isRecording ? "recording" : ""}`}
                    aria-label="Voice input"
                    onClick={toggleRecording}
                  >
                    <FiMic />
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="Type your prompt..."
                  className="prompt-input"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                />
                <button
                  type="button"
                  className="send-icon inline"
                  onClick={send}
                  aria-label="Send prompt"
                >
                  ➤
                </button>
              </div>
            <div className="dropdown-wrapper">
              <div
                className={`model-dropdown ${modelListOpen ? "open" : ""}`}
                role="combobox"
                aria-expanded={modelListOpen}
                ref={dropdownRef}
              >
                  <button
                    type="button"
                    className="model-dropdown-value"
                    onClick={() => setModelListOpen((prev) => !prev)}
                  >
                    {selected[0] || "Select model..."}
                  </button>
                  <div className="model-dropdown-list">
                    {models.map((m) => (
                      <button
                        key={m}
                        type="button"
                        className={`model-option ${selected[0] === m ? "selected" : ""}`}
                        onClick={() => {
                          setSelected([m]);
                          setModelListOpen(false);
                        }}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="units-toggle"
                title={`Toggle units (${weatherUnits === "metric" ? "°C/km/h" : "°F/mph"})`}
                onClick={() => {
                  const next = weatherUnits === "metric" ? "imperial" : "metric";
                  setWeatherUnits(next);
                  try { window.localStorage.setItem("weatherUnits", next); } catch {}
                }}
              >
                {weatherUnits === "metric" ? "°C" : "°F"}
              </button>
            </div>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              multiple
              onChange={handleFileChange}
            />
          </div>

          {attachments.length > 0 && (
            <div className="attachment-list">
              {attachments.map((name, idx) => (
                <span key={`${name}-${idx}`} className="attachment-chip">
                  {name}
                </span>
              ))}
            </div>
          )}
          <div className="model-warning">
            Model Hub can make mistakes. Double-check important information.
          </div>
        </div>
      </div>
    </div>
  );
}
