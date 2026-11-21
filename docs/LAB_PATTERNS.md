# Lab patterns → where they live in CalenDeal

The team uploaded our class labs as the model for how to write code here. This maps each lab pattern to the CalenDeal file that uses it, so anyone (or any Claude session) can follow the same style. The lab files themselves are in the class Claude project ("AI Project"). Copy any you need into `docs/labs/`.

| Lab | Pattern | In CalenDeal |
|---|---|---|
| Lab 1: Semantic search (`semanticSearch.py`, `createChromadb.py`, `jobSearch.py`) | `SentenceTransformer("all-MiniLM-L6-v2")`, Chroma collection with `SentenceTransformerEmbeddingFunction` | `matcher._embed_scores()` (Chroma + MiniLM, cosine). TF-IDF fallback when not installed |
| Lab 2: RAG chatbot (`musicChatbot.py`, `gradioMusicChatbot.py`, `embedMusicChunks.py`) | Retrieve from Chroma → prompt → LLM; Gradio `Blocks` + `Chatbot` | `agent.py` `search_deals` tool (retrieval) + the agent's reply (generation); `app/app.py` Gradio UI |
| Lab 2 + LangSmith (`musicChatbotPydanticLangsmith.py`) | `with_structured_output(PydanticModel)`; LangSmith env vars for tracing | `matcher.Picks`, `local_search.FoundDeals`; LangSmith vars in `.env.example` |
| Lab 4 ext: Structured output (`script1Baseline.py` → `script4HybridRecovery.py`) | Pydantic schema + **bounded** retry instead of trusting the prompt | `llm.structured()` (max 3 tries, returns `None` on failure, caller falls back) |
| Pipeline MAS (`pipelineMAS.py`) | `init_chat_model("provider:model")`, fixed sequence of steps | `llm.get_model()`; the weekly pipeline sources → snapshot → middleware → match → calendar |
| Supervisor MAS (`supervisorMAS.py`) | Routing between specialists | Not used: we chose a **single agent** (`DECISIONS.md` D4) |
| Middleware + HITL (`middlewareHITLMAS 2.py`) | `create_agent(..., middleware=[HumanInTheLoopMiddleware(interrupt_on=...)])`, `InMemorySaver`, resume with `Command(resume={"decisions": [...]})` | `agent.py`: `add_to_calendar` pauses for approval when `hitl_mode == "approve"`; the app's Approve/Reject buttons resume it |
| Middleware (PII, etc.) | Guard what goes in/out of the model | `middleware.py`: expiry + VirusTotal link checks before anything reaches a calendar |
| Lab 4: Fine-tuning (`lab4_fine_tuning1.ipynb`) | — | Not used in v1 |

## House style (from the labs)

- `load_dotenv()` at the entry point; keys only in `.env`.
- `init_chat_model("provider:model")` rather than provider-specific classes, so swapping models is one env var (`CALENDEAL_LLM`).
- Pydantic for anything the LLM must return in a shape; always a bounded retry.
- Keep the prompt in the file next to the code that uses it.
- Evaluate by changing one thing at a time (model, prompt, top-k, retriever) and recording results (`docs/EVALUATION.md`).
