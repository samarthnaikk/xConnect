alias G='export GEMINI_API_KEY="AIzaSyCJ-HFEUIWZe8drZl8KoeGSw8YeytDtNBA"'
alias login_iitm='ssh login_iitm_'
alias login_patheya='ssh mrperfect@97.74.93.241'
function do_venv() {
  if [ -d venv ]; then
    source venv/bin/activate
  else
    python3 -m venv venv && source venv/bin/activate
    if [ -f requirements.txt ]; then
      pip install -r requirements.txt
    fi
  fi
}
