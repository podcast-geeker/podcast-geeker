# Acknowledgments

Podcast Geeker stands on the shoulders of exceptional open-source projects and research. We're grateful to the following communities and contributors.

---

## Core Foundation

### Open Notebook
**Project**: [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook)  
**Author**: [@lfnovo](https://github.com/lfnovo)  
**License**: MIT

Podcast Geeker is built upon the solid foundation of Open Notebook, which provides:
- Three-tier architecture (Next.js + FastAPI + SurrealDB)
- LangGraph workflow orchestration
- Multi-provider AI integration via Esperanto
- Privacy-first design philosophy

We're deeply grateful for this excellent architecture that made our enhancements possible.

---

## Advanced RAG Technologies

### Agentic RAG for Dummies
**Project**: [GiovanniPasq/agentic-rag-for-dummies](https://github.com/GiovanniPasq/agentic-rag-for-dummies)  
**Stars**: 2,054  
**License**: MIT

Inspiration and strategies for:
- **Hierarchical Indexing**: Parent/child chunking for precision + context
- **Query Rewriting**: Intelligent query understanding and reformulation
- **Self-Correction**: Automatic retry with refined queries
- **Conversation Memory**: Maintaining context across questions

We've adapted these LangGraph-based patterns to work seamlessly with SurrealDB's graph database and Podcast Geeker's existing architecture.

### RAG-Anything
**Project**: [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything)  
**Stars**: 13,016  
**License**: MIT

Enables multi-modal document understanding:
- **Image Analysis**: Vision model descriptions of figures and diagrams
- **Table Extraction**: Structured data understanding
- **Equation Parsing**: LaTeX and semantic interpretation
- **MinerU Integration**: Advanced document parsing

Integrated as an optional enhancement layer that gracefully falls back when unavailable.

---

## AI Infrastructure

### Esperanto
**Project**: [lfnovo/esperanto](https://github.com/lfnovo/esperanto)  
**Author**: [@lfnovo](https://github.com/lfnovo)  
**License**: MIT

Unified interface to 16+ AI providers:
- OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, and more
- Smart model selection and fallback logic
- Cost optimization and token management

Esperanto's multi-provider abstraction is central to Podcast Geeker's flexibility.

### LangChain & LangGraph
**Projects**: 
- [langchain-ai/langchain](https://github.com/langchain-ai/langchain)
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)  
**License**: MIT

Powers our intelligent workflows:
- State machine orchestration (LangGraph)
- LLM abstraction and tooling (LangChain)
- Checkpoint persistence for conversation memory
- Streaming responses for real-time UX

All Podcast Geeker workflows (Ask, Chat, Source Processing, Transformations, Podcasts) are built on LangGraph.

---

## Technology Stack

### Frontend
- **[Next.js](https://nextjs.org/)** - React framework with SSR/SSG (MIT License)
- **[React](https://react.dev/)** - UI component library (MIT License)
- **[Shadcn/ui](https://ui.shadcn.com/)** - Component library built on Radix UI (MIT License)
- **[TanStack Query](https://tanstack.com/query)** - Data synchronization (MIT License)
- **[Zustand](https://github.com/pmndrs/zustand)** - State management (MIT License)
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS (MIT License)

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework (MIT License)
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation (MIT License)
- **[Loguru](https://github.com/Delgan/loguru)** - Elegant logging (MIT License)
- **[Pytest](https://pytest.org/)** - Testing framework (MIT License)

### Database
- **[SurrealDB](https://surrealdb.com/)** - Multi-model database (Business Source License 1.1)
  - Graph database with relationships
  - Native vector embeddings
  - Built-in full-text search
  - ACID transactions

### Content Processing
- **[content-core](https://github.com/lfnovo/content-core)** - Multi-format content extraction (MIT License)
- **[PyMuPDF](https://pymupdf.readthedocs.io/)** - PDF processing (AGPL License)
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** - HTML parsing (MIT License)

### Podcast Generation
- **[podcast-creator](https://github.com/lfnovo/podcast-creator)** - Multi-speaker podcast generation (MIT License)
- **OpenAI TTS** / **ElevenLabs** / **Google TTS** - Text-to-speech services

---

## Academic Context

### Research Influences
- **Self-RAG**: "Self-RAG: Learning to Retrieve, Generate, and Critique" (ICLR 2024)
- **Hierarchical Retrieval**: Concepts from Agentic RAG research
- **Multi-Modal RAG**: RAG-Anything paper and implementation
- **Query Understanding**: LangChain documentation and best practices

---

## Community & Support

### Open Source Community
Huge thanks to all contributors, bug reporters, feature requesters, and community members who make this project better every day.

### Discord Community
Special thanks to the Podcast Geeker Discord community for feedback, testing, and feature ideas.

**Join us**: [Discord Server](https://discord.gg/37XJPXfz2w)

---

## License Compliance

All third-party libraries and projects used in Podcast Geeker are properly licensed and attributed:

- **MIT License**: Permits commercial use, modification, distribution, and private use
- **AGPL License**: Copyleft license requiring derivative works to be open-sourced
- **Business Source License**: SurrealDB's license permits free use with specific production limits

We comply with all license requirements including:
- ✅ Preserving copyright notices
- ✅ Including license text
- ✅ Attributing original authors
- ✅ Documenting modifications (see `docs/2-CORE-CONCEPTS/agentic-rag-enhancement.md`)

Full license texts are available in the `licenses/` directory of this repository.

---

## Contributing

If we've missed acknowledging any project or contributor, please let us know:
- Open an issue: [GitHub Issues](https://github.com/podcast-geeker/podcast-geeker/issues)
- Join our Discord: [Community Server](https://discord.gg/37XJPXfz2w)

---

**Last Updated**: February 2026  
**Podcast Geeker Version**: 1.0.0  
**License**: MIT (see LICENSE file)
