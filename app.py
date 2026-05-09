import streamlit as st

import json
import requests
import subprocess
import os
from modes.orchestrator import run_assistant

st.set_page_config(page_title="Lokr Assistant", layout="wide")

# Load Custom Sentinel Theme
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Fetch available Ollama models
@st.cache_data(ttl=60)
def get_ollama_models():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [m["name"] for m in models] if models else ["qwen2.5-coder:7b"]
    except Exception:
        pass
    return ["qwen2.5-coder:7b"]

available_models = get_ollama_models()

st.sidebar.title("Lokr Assistant")
project_dir = st.sidebar.text_input("Project Directory", value="./lokr-demo-app")

if st.sidebar.button("Re-index Project", disabled=not project_dir):
    with st.spinner("Indexing project... (this may take a few minutes)"):
        # Check for local submodule first, then environment variable, then fallback
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_lokr = os.path.join(current_dir, "lokr_core")
        lokr_path = os.environ.get("LOKR_PATH", local_lokr if os.path.exists(local_lokr) else "/home/anas/dev-oracle")
        venv_python = os.path.join(lokr_path, ".venv", "bin", "python")
        main_py = os.path.join(lokr_path, "main.py")
        config_yaml = os.path.join(lokr_path, "config.yaml")
        
        cmd = f'cd "{project_dir}" && "{venv_python}" "{main_py}" --index --config "{config_yaml}"'
        
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output_container = st.sidebar.empty()
        full_output = ""
        
        for line in process.stdout:
            full_output += line
            output_container.code(full_output)
            
        process.wait()
        
        if process.returncode == 0:
            st.sidebar.success("Project indexed successfully. Ready for analysis.")
        else:
            st.sidebar.error(f"Indexing failed with return code {process.returncode}")

use_lokr = st.sidebar.checkbox("Use Lokr context", value=True)

import os
env_api_key = os.environ.get("API_KEY", "")

if "api_choice" not in st.session_state:
    st.session_state.api_choice = "Remote API" if env_api_key else "Local (Ollama)"

api_choice = st.sidebar.radio("LLM Provider", ["Local (Ollama)", "Remote API (OpenAI-Compatible)"], 
                              index=1 if st.session_state.api_choice == "Remote API" else 0)

if api_choice == "Local (Ollama)":
    api_type = "ollama"
    base_url = st.sidebar.text_input("Ollama Base URL", value="http://localhost:11434", help="If running on a public space, use an Ngrok URL to connect to your local Ollama.")
    api_key = ""
    default_idx = available_models.index("qwen2.5-coder:7b") if "qwen2.5-coder:7b" in available_models else 0
    model_choice = st.sidebar.selectbox("Model", available_models + ["Custom..."], index=default_idx)
    if model_choice == "Custom...":
        model = st.sidebar.text_input("Custom Model Name", value="qwen2.5-coder:7b")
    else:
        model = model_choice
else:
    api_type = "openai"
    base_url = st.sidebar.text_input("API Base URL", value="https://api.groq.com/openai/v1")
    model = st.sidebar.text_input("Model Name", value="llama-3.3-70b-versatile")
    api_key = st.sidebar.text_input("API Key", value=env_api_key, type="password")
st.sidebar.info("Describe your problem or question in the main area. The assistant will automatically determine the best workflow.")

# Custom Header
st.markdown('<h1 class="main-title">🛡️ LOKR SENTINEL</h1>', unsafe_allow_html=True)
st.markdown('<p style="margin-top: -30px; opacity: 0.7; font-weight: 300;">Multi-Agent Codebase Defense & Orchestration</p>', unsafe_allow_html=True)
# Initialize session state for history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for history management
with st.sidebar:
    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "result" in msg:
            with st.expander("Technical Trace"):
                st.json(msg["result"])

# User input
user_input = st.chat_input("What do you need help with?")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # Sentinel Live Feed
        st.markdown("### 📡 SENTINEL LIVE FEED")
        live_feed = st.empty()
        feed_content = []

        with st.status("Initializing Agents…", expanded=True) as status:
            def progress(msg):
                feed_content.append(msg)
                # Show only the last 5 lines for a scrolling "terminal" effect
                display_text = "\n\n".join(feed_content[-5:])
                live_feed.markdown(f'<div class="glass-container" style="padding:15px; border-left: 3px solid var(--primary-neon); background: rgba(0,0,0,0.2); font-family: monospace; font-size: 0.9rem;">{display_text}</div>', unsafe_allow_html=True)
                status.write(f"⏳ {msg}")
            
            # Pass history to orchestrator
            import time
            result = run_assistant(
                user_input=user_input,
                project_path=project_dir if use_lokr else None,
                model=model,
                use_lokr=use_lokr,
                progress_callback=progress,
                api_type=api_type,
                base_url=base_url,
                api_key=api_key,
                history=st.session_state.messages[:-1]
            )
            time.sleep(1) # Final pause for dramatic effect
            status.update(label="SENTINEL ANALYSIS COMPLETE ✅", state="complete")
        
        # --- SENTINEL PREMIUM REPORT ---
        mode = result.get("mode", "analysis")
        analysis = result.get("analysis", {})
        action = result.get("action", {})
        safety = result.get("safety", {})
        validation = result.get("validation", {})
        
        if result.get("type") == "explain":
            st.markdown(result.get("answer", ""))
            with st.expander("View Code Context"):
                st.text(result.get("context", ""))
        else:
            # 1. MAIN VERDICT
            verdict_icon = "✅" if result.get("status") == "success" else "❌"
            mode_label = mode.upper()
            st.markdown(f"### {mode_label} RESULT: {verdict_icon} {result.get('status', 'COMPLETE').upper()}")
            
            if mode == "repair" and result.get("status") == "success":
                st.success(f"**Root Cause:** {analysis.get('hypothesis', 'Issue identified and patched.')}")
            
            st.divider()

            # 2. CONTEXT USED
            classification = result.get("classification", {})
            files = classification.get("files_to_analyze", [])
            if files:
                st.markdown("#### 🔍 Context Used")
                for f in files:
                    st.write(f"• `{f}`")
                st.divider()

            # 3. MODE-AWARE RESULTS SECTION
            if mode == "repair":
                col_diag, col_patch = st.columns([1, 1])
                with col_diag:
                    st.markdown("#### 🔍 Diagnosis & Evidence")
                    execution_trace = analysis.get("execution_trace")
                    if execution_trace:
                        st.markdown("**Execution Trace:**")
                        st.code(execution_trace, language="text")
                    
                    findings = analysis.get("findings", [])
                    if findings:
                        for f in findings:
                            st.error(f"**Issue:** {f.get('issue', 'Unknown')}\n\n**File:** `{f.get('file', 'Unknown')}:{f.get('line', '?')}`\n\n**Impact:** {f.get('impact', 'Unknown')}")
                            st.markdown("**Evidence:**")
                            st.code(f.get('evidence', ''), language="javascript")
                    else:
                        st.info(analysis.get("hypothesis", "No grounded findings provided."))
                
                with col_patch:
                    st.markdown("#### 🛠️ Proposed Fix")
                    patch = result.get("final_patch") or action.get("patch", "")
                    if patch:
                        if "--- " in patch or "diff --git" in patch:
                            st.code(patch, language="diff")
                        else:
                            buggy = analysis.get("findings", [""])[0] if analysis.get("findings") else ""
                            if buggy:
                                if isinstance(buggy, dict):
                                    buggy_text = buggy.get("issue", "")
                                else:
                                    buggy_text = str(buggy)
                                st.code(f"- {buggy_text}\n+ {patch}", language="diff")
                            else:
                                st.code(patch, language="javascript")
                    else:
                        st.info("No patch generated.")

            elif mode == "review":
                st.subheader("📝 Review Assessment")
                st.markdown(f"**Change Summary:** {analysis.get('changes_summary', '')}")
                st.markdown(f"**Change Type:** {analysis.get('change_type', '')}")

                if action.get("observations"):
                    st.markdown("**Observations:**")
                    for obs in action["observations"]:
                        st.markdown(f"- {obs}")
                if action.get("recommendations"):
                    st.markdown("**Recommendations:**")
                    for rec in action["recommendations"]:
                        st.markdown(f"- {rec}")
                if action.get("suggestion_priority"):
                    st.markdown(f"**Priority:** {action['suggestion_priority']}")

                decision = result.get("approval", "UNKNOWN")
                color = "red" if decision == "REQUEST_CHANGES" else "green"
                st.markdown(f"### Decision: :{color}[{decision}]")

            elif mode == "prevent":
                st.subheader("🛡️ Deployment Readiness")
                st.metric("Readiness Score", f"{analysis.get('readiness_score', 0.0):.2f}")
                
                blockers = action.get("blockers", [])
                if blockers:
                    st.error("Blockers:")
                    for b in blockers:
                        st.markdown(f"- {b}")
                warnings = action.get("warnings", [])
                if warnings:
                    st.warning("Warnings:")
                    for w in warnings:
                        st.markdown(f"- {w}")
                recommendations = action.get("recommendations", [])
                if recommendations:
                    st.info("Recommendations:")
                    for r in recommendations:
                        st.markdown(f"- {r}")

                go_no_go = safety.get("go_no_go", "UNKNOWN")
                color = "green" if go_no_go == "SAFE_TO_DEPLOY" else ("orange" if "CAUTION" in go_no_go else "red")
                st.markdown(f"### Verdict: :{color}[{go_no_go}]")

            # 4. SAFETY & RISK
            st.divider()
            st.markdown("### 🛡️ Safety & Risk")
            s_col1, s_col2, s_col3 = st.columns(3)
            risk_score = safety.get("risk_score", 0.0)
            risk_level = "LOW" if risk_score < 0.3 else ("MEDIUM" if risk_score < 0.7 else "HIGH")
            s_col1.metric("Risk Level", risk_level)
            s_col2.metric("Risk Score", risk_score)
            
            if mode == "prevent":
                is_safe = safety.get("go_no_go", "") == "SAFE_TO_DEPLOY"
            else:
                is_safe = safety.get("safe", False)
                
            s_col3.write(f"**Verdict:** {'✅ SAFE' if is_safe else '⚠️ WARNING'}")
            for w in safety.get("warnings", []):
                st.warning(w)

            # 5. INVESTIGATION TIMELINE (THE TRACE)
            st.divider()
            st.markdown("### ⏱️ Investigation Timeline (Trace)")
            st.caption("Step-by-step reasoning from the Sentinel multi-agent core.")

            raw_hypotheses = result.get("_raw_hypotheses", [])
            raw_actions = result.get("_raw_actions", [])
            raw_safety = result.get("_raw_safety", [])
            raw_validations = result.get("_raw_validations", [])

            # --- Agent 1: Analyzer ---
            if analysis:
                st.markdown('<div class="timeline-agent">', unsafe_allow_html=True)
                st.markdown("#### 1. 🔍 Analyzer")
                st.markdown(f"**Hypothesis:** {analysis.get('hypothesis', 'Hypothesis generated.')}")
                
                findings = analysis.get('findings', [])
                if findings:
                    st.markdown("**Key Findings:**")
                    for f in findings:
                        if isinstance(f, dict):
                            st.markdown(f"- **{f.get('issue', 'Issue')}**: {f.get('impact', '')}")
                        else:
                            st.markdown(f"- {f}")
                
                cot = raw_hypotheses[-1].get("chain_of_thought", []) if raw_hypotheses else []
                if cot:
                    with st.expander("View Analyzer Reasoning"):
                        for s in cot: st.markdown(f"- {s}")
                st.markdown('</div>', unsafe_allow_html=True)

            # --- Agent 2: Action ---
            if action:
                st.markdown('<div class="timeline-agent" style="border-color: #bc00ff;">', unsafe_allow_html=True)
                st.markdown("#### 2. 🛠️ Action Agent")
                st_label = "Patch generated" if mode == "repair" else "Observations drafted"
                st.markdown(f"**Result:** {st_label}")
                
                if mode == "repair" and action.get("patch"):
                    with st.expander("View Patch Summary"):
                        st.code(action.get("patch")[:500] + ("..." if len(action.get("patch", "")) > 500 else ""), language="javascript")
                
                cot = raw_actions[-1].get("chain_of_thought", []) if raw_actions else []
                if cot:
                    with st.expander("View Action Reasoning"):
                        for s in cot: st.markdown(f"- {s}")
                st.markdown('</div>', unsafe_allow_html=True)

            # --- Agent 3: Safety ---
            if safety:
                st.markdown('<div class="timeline-agent" style="border-color: #00ff88;">', unsafe_allow_html=True)
                st.markdown("#### 3. 🛡️ Safety Agent")
                if mode == "prevent":
                    is_safe_trace = safety.get("go_no_go", "") == "SAFE_TO_DEPLOY"
                else:
                    is_safe_trace = safety.get("safe", False)
                st.markdown(f"**Verdict:** {'✅ PASS' if is_safe_trace else '⚠️ WARNING/REJECTED'}")
                st.markdown(f"**Reasoning:** {safety.get('reasoning', 'Evaluated deployment risk.')}")
                
                cot = raw_safety[-1].get("chain_of_thought", []) if raw_safety else []
                if cot:
                    with st.expander("View Safety Reasoning"):
                        for s in cot: st.markdown(f"- {s}")
                st.markdown('</div>', unsafe_allow_html=True)

            # --- Agent 4: Validator ---
            if validation:
                st.markdown('<div class="timeline-agent" style="border-color: #ffaa00;">', unsafe_allow_html=True)
                st.markdown("#### 4. ✅ Validator")
                st.markdown(f"**Feedback:** {validation.get('feedback', 'Validation complete.')}")
                
                cot = raw_validations[-1].get("chain_of_thought", []) if raw_validations else []
                if cot:
                    with st.expander("View Validator Reasoning"):
                        for s in cot: st.markdown(f"- {s}")
                st.markdown('</div>', unsafe_allow_html=True)

            with st.expander("Show full JSON"):
                st.json(result)

        # Store for session history
        st.session_state.messages.append({"role": "assistant", "content": "Analysis complete.", "result": result})
