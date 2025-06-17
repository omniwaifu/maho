# Upstream Changes Analysis (Detailed)

## 🟢 SAFE TO CHERRY-PICK (Low risk, no async/architecture conflicts)

### UI/Frontend improvements:
- ✅ 552d9db: markdown headings (CSS only) - **ALREADY IN MAHO** (font-weight + margin for h1-h6)
- ❌ ae2d959: katex fix (webui JS + prompts) - **CONFLICTS WITH MAHO'S MATH RENDERING**
- ❌ ea708e6: katex fix (webui JS + prompts) - **CONFLICTS WITH MAHO'S MATH RENDERING**  
- ✅ be067ad: render markdown in response bubbles (webui only) - **SAFE TO TAKE**
- ✅ 560c2a6: simplify katex rendering delimiters (webui only) - **SAFE TO TAKE**
- ❌ 9c8703c: render file paths as clickable links (webui only) - **CONFLICTS - this is actually RAG tool changes**

### Build/Docker fixes:
- ✅ 80abbdd: torch version fix, cron chmod fix (docker scripts) - **SAFE TO TAKE**
- ✅ 8edcb95: x86 build fix + build cleanup (docker cleanup) - **SAFE TO TAKE**

### Prompts improvements:
- ✅ f9e6861: encourage markdown formatting in AI responses - **PERFECT ADDITION**
  ```
  + always use markdown for formatting including headers bold text and lists to improve readability
  ```
- ✅ 1785be5: fix typo in prompt - **TRIVIAL TYPO FIX**
  ```diff
  - !!! Supported document dormats: HTML, PDF...  
  + !!! Supported document formats: HTML, PDF...
  ```

## 🟡 MODERATE RISK (Might need adaptation for maho's architecture)

### Code execution improvements:
- ✅ 1f33bfc: dialog detection in code exec - **EXCELLENT FEATURE** 
  - Adds smart dialog detection (Y/N, yes/no, :, ?) in code output
  - Returns control to agent when dialogs detected after 5s timeout
  - Adds new prompt: `fw.code.pause_dialog.md`
  - **SHOULD DEFINITELY TAKE** - no async conflicts, pure improvement

### RAG/Search improvements:
- ⚠️ 11f7c60: rag tool progress and optimization (python/helpers/, python/tools/) - **MODERATE - CHECK PATHS**
- ⚠️ 602d60c: searxng config radio, todos cleanup - **CHECK FOR CONFLICTS**
- ⚠️ a9d3987: RAG tool merge - **MASSIVE CHANGE - 1541 insertions, adds new document_query system**

## 🔴 HIGH RISK (Likely conflicts with maho's async refactor)

### Core agent/async changes:
- 🚫 73e6855: agent response improvements - **MASSIVE UI REFACTOR + agent.py changes (814 insertions)**  
- ✅ de39128: security fix (python/helpers/memory.py) - **CRITICAL SECURITY FIX**
  ```diff
  - return eval(condition, {}, data)  # DANGEROUS!
  + return ast.literal_eval(condition, {}, data)  # SAFE
  ```

## 📋 FINAL RECOMMENDATIONS

### 🎯 MUST TAKE (High value, low risk):
1. **f9e6861**: Markdown formatting encouragement (one line addition)
2. **1785be5**: Typo fix (trivial fix)  
3. **de39128**: Security fix (fixes eval() vulnerability)
4. **1f33bfc**: Dialog detection (excellent UX improvement)

### 🔧 DOCKER IMPROVEMENTS (Safe but check paths):
5. **80abbdd**: Torch version fix + cron chmod
6. **8edcb95**: x86 build fix + cleanup

### ⚠️ EVALUATE CASE-BY-CASE:
- **be067ad**: Markdown in response bubbles (check UI conflicts)
- **a9d3987**: RAG tool merge (huge feature - separate evaluation)

### 🚫 SKIP (Will conflict):
- **ae2d959, ea708e6**: KaTeX approach conflicts with maho
- **73e6855**: Massive UI changes will conflict with maho's layout
- **9c8703c**: Mislabeled - actually part of RAG changes 