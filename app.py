import streamlit as st
import json
import requests
import subprocess
import os
from modes.orchestrator import run_assistant

st.set_page_config(page_title="Lokr Assistant", layout="wide")

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
project_dir = st.sidebar.text_input("Project Directory", value="/home/anas/Desktop/FILES NEEDED/pet-ai-render")

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

st.sidebar.markdown("---")
api_choice = st.sidebar.radio("LLM Provider", ["Local (Ollama)", "Remote API (OpenAI-Compatible)"])

if api_choice == "Local (Ollama)":
    api_type = "ollama"
    base_url = "http://localhost:11434"
    api_key = ""
    default_idx = available_models.index("qwen2.5-coder:7b") if "qwen2.5-coder:7b" in available_models else 0
    model = st.sidebar.selectbox("Model", available_models, index=default_idx)
else:
    api_type = "openai"
    base_url = st.sidebar.text_input("API Base URL", value="https://api.groq.com/openai/v1")
    model = st.sidebar.text_input("Model Name", value="llama3-70b-8192")
    api_key = st.sidebar.text_input("API Key", type="password")
st.sidebar.info("Describe your problem or question in the main area. The assistant will automatically determine the best workflow.")

st.title("🤖 AI Engineering Assistant")
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
        with st.status("Running agents…", expanded=True) as status:
            def progress(msg):
                status.write(f"⏳ {msg}")
            
            # Pass history to orchestrator
            result = run_assistant(
                user_input=user_input,
                project_path=project_dir if use_lokr else None,
                model=model,
                use_lokr=use_lokr,
                progress_callback=progress,
                api_type=api_type,
                base_url=base_url,
                api_key=api_key,
                history=st.session_state.messages[:-1] # Exclude the current message
            )
            status.update(label="Analysis complete ✅", state="complete")
        
        # Determine the answer content
        if result.get("type") == "explain":
            answer = result.get("answer", "")
        else:
            # For pipeline results, summarize based on mode
            mode = result.get("mode", "analysis")
            analysis = result.get("analysis", {})
            
            if mode == "repair":
                status = result.get("status", "unknown")
                verdict = "✅ FIXED" if status == "success" else ("⚠️ NEEDS REVIEW" if status == "failed" else f"⚠️ {status.upper()}")
                summary = analysis.get("diagnosis", result.get("validation", {}).get("feedback", "No summary available."))
                answer = f"### Repair Result: {verdict}\n\n{summary}"
            elif mode == "review":
                approval = result.get("approval", "UNKNOWN")
                summary = analysis.get("changes_summary", "No summary available.")
                answer = f"### Review Result: {approval}\n\n{summary}"
            elif mode == "prevent":
                approval = result.get("approval", "UNKNOWN")
                summary = analysis.get("change_summary", "No summary available.")
                answer = f"### Deployment Assessment: {approval}\n\n{summary}"
            else:
                answer = f"### {mode.capitalize()} Result\n\nAnalysis complete."
            
        st.markdown(answer)
        
        # Store assistant response
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "result": result
        })
        
        if result.get("type") == "explain":
            with st.expander("View Code Context"):
                st.text(result.get("context", ""))
        elif result.get("type") == "pipeline":
            st.subheader("Pipeline Result")
            
            # Common Status
            wf_status = result.get("status")
            if wf_status == "success":
                st.success("Workflow completed successfully.")
            elif wf_status == "refused":
                st.error("The analysis was refused by the model.")
            elif wf_status in ["failure", "failed"]:
                st.error("Workflow finished with status: failure.")
            else:
                st.warning(f"Workflow finished with status: {wf_status}")
            
            mode = result.get("mode")
            analysis = result.get("analysis", {})
            action = result.get("action", {})
            safety = result.get("safety", {})
            validation = result.get("validation", {})
            classification = result.get("classification", {})
            
            confidence = classification.get("confidence", 0.0)
            if confidence > 0 and confidence < 0.5:
                st.warning("⚠️ Low confidence — manual review recommended")
                
            files = []
            files.extend(classification.get("files_to_analyze", []))
            if isinstance(analysis, dict):
                files.extend(analysis.get("files_changed", []))
                files.extend(analysis.get("evidence_used", []))
            
            files = list(set([f for f in files if isinstance(f, str)]))[:5]
            if files:
                st.markdown("### 🔍 Context Used")
                for f in files:
                    st.write(f"• `{f}`")
            st.markdown("---")
            
            if mode == "repair":
                evidence_used = analysis.get("evidence_used", [])
                classification_files = result.get("classification", {}).get("files_to_analyze", [])
                primary_file = evidence_used[0] if evidence_used else (classification_files[0] if classification_files else "unknown file")
                diag_issue = (analysis.get("diagnosis", "") or (analysis.get("issues", [{}])[0].get("description", "") if analysis.get("issues") else ""))[:200]
                confidence = classification.get("confidence", 0.0)
                conf_color = "green" if confidence >= 0.8 else ("orange" if confidence >= 0.5 else "red")
                
                if primary_file == "unknown file" and not diag_issue:
                    st.markdown(f"Analysis completed. (Confidence: :{conf_color}[**{confidence:.1f}**])")
                else:
                    st.markdown(f"Analyzed: {primary_file}  \nIssue: {diag_issue}  \nConfidence: :{conf_color}[**{confidence:.1f}**]")
                    
                st.markdown("### Diagnosis")
                st.write(analysis.get("diagnosis", "No diagnosis provided."))
                
                st.markdown("### Proposed Fix")
                patch = analysis.get("final_patch") or result.get("final_patch") or action.get("patch", "")
                st.code(patch, language="javascript")
                
                st.markdown("### Safety & Risk")
                col1, col2 = st.columns(2)
                risk_score = safety.get("risk_score", 0)
                risk_level = "Low" if float(risk_score) < 0.3 else ("Medium" if float(risk_score) <= 0.7 else "High")
                col1.metric("Risk Level", risk_level, f"{risk_score}", delta_color="inverse")
                
                is_safe = safety.get("safe", False)
                verdict = "✅ Safe to apply" if is_safe else "⚠️ Needs review"
                col2.markdown(f"**Verdict:** {verdict}")
                
                st.markdown("### Validation Feedback")
                st.info(validation.get("feedback", "No feedback."))
                
            elif mode == "review":
                confidence = classification.get("confidence", 0.0)
                conf_color = "green" if confidence >= 0.8 else ("orange" if confidence >= 0.5 else "red")
                st.markdown(f"Reviewed: {', '.join(analysis.get('files_affected', ['unknown']))}  \nChange type: {analysis.get('change_type', 'unknown')}  \nConfidence: :{conf_color}[**{confidence:.1f}**]")
                
                st.markdown("### Change Summary")
                st.write(analysis.get("changes_summary", ""))
                
                st.markdown(f"**Change Type:** {analysis.get('change_type', 'Unknown')}")
                
                decision = result.get("approval", "UNKNOWN")
                color = "green" if decision == "APPROVE" else ("orange" if decision == "REQUEST_CHANGES" else "red")
                st.markdown(f"**Decision:** :{color}[**{decision}**]")
                
                st.markdown("### Files Affected")
                for f in analysis.get("files_affected", []):
                    st.markdown(f"- {f}")
                    
                st.markdown("### Observations")
                for i, obs in enumerate(action.get("observations", []), 1):
                    st.markdown(f"{i}. {obs}")
                    
                st.markdown("### Recommendations")
                for rec in action.get("recommendations", []):
                    st.markdown(f"- {rec}")
                    
                st.markdown(f"**Deployment Risk:** {safety.get('deployment_risk', 'Unknown')}")
                
                st.markdown("### Review Checklist")
                for item in validation.get("review_checklist", []):
                    st.markdown(f"- [ ] {item}")
                    
            elif mode == "prevent":
                st.markdown(f"Assessed: {', '.join(analysis.get('files_changed', ['unknown']))}  \nReadiness score: {analysis.get('readiness_score', '?')}")
                
                st.markdown("### Readiness Assessment")
                score = analysis.get("readiness_score", 0)
                try:
                    score_float = float(score)
                except (ValueError, TypeError):
                    score_float = 0.0
                st.progress(score_float, text=f"Readiness Score: {score_float:.2f}")
                
                decision = result.get("approval", "UNKNOWN")
                color = "green" if decision == "SAFE_TO_DEPLOY" else ("orange" if decision == "PROCEED_WITH_CAUTION" else "red")
                st.markdown(f"**Go/No-Go:** :{color}[**{decision}**]")
                
                st.markdown("### Files Changed")
                for f in analysis.get("files_changed", []):
                    st.markdown(f"- {f}")
                
                blockers = action.get("blockers", [])
                if blockers:
                    st.markdown("### Blockers")
                    for b in blockers:
                        st.error(b)
                
                warnings = action.get("warnings", [])
                if warnings:
                    st.markdown("### Warnings")
                    for w in warnings:
                        st.warning(w)
                        
                st.markdown("### Recommendations")
                for rec in action.get("recommendations", []):
                    st.markdown(f"- {rec}")
                    
                st.markdown(f"**Deployment Risk:** {safety.get('deployment_risk', 'Unknown')}")
                
                st.markdown("### Health Checks")
                for hc in safety.get("health_checks", []):
                    st.markdown(f"- {hc}")
                    
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Pre-deploy Checklist")
                    for item in validation.get("pre_deploy_checklist", []):
                        st.markdown(f"- [ ] {item}")
                with col2:
                    st.markdown("### Post-deploy Checklist")
                    for item in validation.get("post_deploy_checklist", []):
                        st.markdown(f"- [ ] {item}")
                        
            st.markdown("---")
            with st.expander("⏱️ Investigation Timeline (Trace)"):
                st.markdown("This timeline shows the exact reasoning steps the agents took.")
                if analysis:
                    diag = analysis.get("diagnosis", analysis.get("changes_summary", analysis.get("change_summary", "Analyzed the code context.")))
                    st.info(f"**1. 🔍 Analyzer** → {diag}")
                if action:
                    if mode == "prevent":
                        act_summary = f"Identified {len(action.get('blockers', []))} blocker(s) and {len(action.get('warnings', []))} warning(s)."
                    elif mode == "repair":
                        act_summary = "Proposed a code patch to resolve the diagnosed issue."
                    else:
                        obs = action.get("observations", ["Generated review observations."])
                        act_summary = obs[0] if obs else "Generated review observations."
                    st.info(f"**2. 🛠️ Action Agent** → {act_summary}")
                if safety:
                    saf_summary = safety.get("reasoning", "Evaluated deployment risk.")
                    st.info(f"**3. 🛡️ Safety Agent** → {saf_summary}")
                if validation:
                    val_summary = validation.get("feedback", "Verified the proposed changes.")
                    st.info(f"**4. ✅ Validator** → {val_summary}")
                        
            with st.expander("Show full JSON"):
                st.json(result)
        else:
            st.subheader("Result")
            with st.expander("Show full JSON"):
                st.json(result)
