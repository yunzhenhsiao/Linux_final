"""
TransitFlow — Gradio Web Interface
====================================
Run with:  python skeleton/ui.py
Then open: http://localhost:7860

Students: You do NOT need to change this file.
"""

import sys
sys.path.insert(0, ".")

import gradio as gr
from skeleton.agent import run_agent
from skeleton.llm_provider import llm
from skeleton.config import GEMINI_CHAT_MODEL, OLLAMA_CHAT_MODEL
from databases.relational.queries import (
    login_user,
    register_user,
    get_user_secret_question,
    verify_secret_answer,
    update_password,
    get_user_role,
    query_employee_operations_summary,
    query_admin_all_users,
    query_admin_system_stats,
    query_admin_top_passengers,
    query_admin_policy_list,
)
from skeleton.cache import invalidate_cache
from skeleton.tasks import app as celery_app

SECRET_QUESTIONS = [
    "What is the name of your first pet?",
    "What is your mother's maiden name?",
    "What city were you born in?",
    "What was the name of your first school?",
    "What is your favourite book?",
    "What was the make of your first car?",
]


# ── Chat handler ───────────────────────────────────────────────────────────────

def chat(user_message: str, history_display: list, agent_history: list,
         show_debug: bool, current_user: str):
    if not user_message.strip():
        return history_display, agent_history, gr.update()

    if show_debug:
        answer, new_agent_history, debug_text = run_agent(
            user_message, agent_history, debug=True, current_user_email=current_user
        )
    else:
        answer, new_agent_history = run_agent(
            user_message, agent_history, debug=False, current_user_email=current_user
        )
        debug_text = ""

    history_display = history_display + [
        {"role": "user",      "content": user_message},
        {"role": "assistant", "content": answer},
    ]

    debug_update = gr.update(value=debug_text, visible=show_debug)
    return history_display, new_agent_history, debug_update


def clear_conversation():
    return [], [], gr.update(value="", visible=False)


# ── Provider / model selection ────────────────────────────────────────────────

_KNOWN_OLLAMA_MODELS = ["llama3.2:1b", "llama3.1:8b"]


def get_ollama_status():
    if llm.ollama_available():
        return "🟢 Ollama is running locally"
    return "🔴 Ollama not detected — install from ollama.com and run `ollama pull " + OLLAMA_CHAT_MODEL + "`"


def get_chat_model_choices() -> list:
    available = set(llm.get_available_ollama_models())
    choices = []
    for m in _KNOWN_OLLAMA_MODELS:
        label = m if m in available else f"{m}  (not pulled)"
        choices.append((label, m))
    choices.append((f"☁️ Gemini ({GEMINI_CHAT_MODEL})", "gemini"))
    return choices


def get_initial_chat_model_value() -> str:
    return "llama3.2:1b"


def on_chat_model_change(value: str):
    if value == "gemini":
        status = llm.set_chat_provider("gemini")
        return f"**Active:** ☁️ Gemini ({GEMINI_CHAT_MODEL})\n\n{status}", get_ollama_status()
    available = set(llm.get_available_ollama_models())
    if value not in available:
        return f"⚠️ `{value}` is not pulled. Run: `ollama pull {value}`", get_ollama_status()
    llm.set_chat_provider("ollama")
    status = llm.set_chat_model(value)
    return f"**Active:** {value}\n\n{status}", get_ollama_status()


# ── Auth handlers ──────────────────────────────────────────────────────────────

def do_login(email: str, password: str):
    """Handle login form submission."""
    if not email.strip() or not password.strip():
        return (
            gr.update(value="Please enter your email and password.", visible=True),
            None,
            None,  # user_role
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=True),
        )

    user = login_user(email.strip(), password)
    if user is None:
        return (
            gr.update(value="Incorrect email or password.", visible=True),
            None,
            None,  # user_role
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=True),
        )

    # Get user role
    user_role = get_user_role(email.strip())
    
    display_name = f"{user['first_name']} {user['surname']}"
    return (
        gr.update(value="", visible=False),
        user["email"],
        user_role,  # user_role
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=f"**Welcome, {display_name}** ({user_role})", visible=True),
        gr.update(visible=True),
        gr.update(visible=False),
    )


def do_logout():
    return (
        None,
        None,  # user_role
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(value="", visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def do_register(email, first_name, surname, year_of_birth, password, secret_question, secret_answer, identity_key):
    """Handle registration form submission."""
    if not all([
        str(email).strip(), str(first_name).strip(), str(surname).strip(),
        str(password).strip(), secret_question, str(secret_answer).strip(),
    ]):
        return (
            gr.update(value="All fields are required.", visible=True),
            None,
            None,  # user_role
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=True),
        )

    try:
        year = int(year_of_birth)
        if year < 1900 or year > 2015:
            raise ValueError
    except (ValueError, TypeError):
        return (
            gr.update(value="Please enter a valid year of birth (e.g. 1990).", visible=True),
            None,
            None,  # user_role
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=True),
        )

    # Determine role based on identity key
    from skeleton.config import EMPLOYEE_KEY, ADMIN_KEY
    user_role = "passenger"  # default
    if identity_key and identity_key.strip():
        if identity_key.strip() == ADMIN_KEY:
            user_role = "admin"
        elif identity_key.strip() == EMPLOYEE_KEY:
            user_role = "employee"

    ok, err = register_user(
        email.strip(), first_name.strip(), surname.strip(),
        year, password, secret_question, secret_answer.strip(),
        role=user_role,
    )
    if not ok:
        return (
            gr.update(value=err, visible=True),
            None,
            None,  # user_role
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(visible=True),
        )

    display_name = f"{first_name.strip()} {surname.strip()}"
    return (
        gr.update(value="", visible=False),
        email.strip().lower(),
        user_role,  # user_role
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=f"**Welcome, {display_name}** ({user_role})", visible=True),
        gr.update(visible=True),
        gr.update(visible=False),
    )


def forgot_find_question(email: str):
    """Step 1 — look up the secret question for the given email."""
    if not email.strip():
        return (
            gr.update(value="Please enter your email address.", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    question = get_user_secret_question(email.strip())
    if question is None:
        return (
            gr.update(value="No account found with that email address.", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    return (
        gr.update(value="", visible=False),
        gr.update(value=f"**Your security question:** {question}", visible=True),
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(visible=True),
    )


def forgot_reset_password(email: str, answer: str, new_password: str):
    """Step 2 — verify the secret answer and update the password."""
    if not str(answer).strip() or not str(new_password).strip():
        return gr.update(value="Please fill in all fields.", visible=True)

    if not verify_secret_answer(email.strip(), answer.strip()):
        return gr.update(value="Incorrect answer. Please try again.", visible=True)

    if not update_password(email.strip(), new_password):
        return gr.update(value="Failed to update password. Please try again.", visible=True)

    return gr.update(value="**Password reset successfully. You can now log in.**", visible=True)


# ── Panel visibility toggles ──────────────────────────────────────────────────

def show_login_panel():
    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

def show_register_panel():
    return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)

def show_forgot_panel():
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

def hide_all_panels():
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


# ── Employee dashboard functions ──────────────────────────────────────────

def load_employee_operations_summary():
    """Load and format employee operations summary."""
    try:
        data = query_employee_operations_summary()
        stats = data.get("today_stats", {})
        occupancy = data.get("occupancy", [])
        
        md = "### Today's Operations Summary\n\n"
        md += f"**Total Bookings:** {stats.get('total_bookings', 0)}\n"
        md += f"**Total Revenue:** ${stats.get('total_revenue', 0):.2f}\n"
        md += f"**Unique Passengers:** {stats.get('unique_passengers', 0)}\n\n"
        
        md += "### Schedule Occupancy\n"
        if occupancy:
            md += "| Line | Route | Booked | Total | Occupancy %|\n|---|---|---|---|---|\n"
            for row in occupancy:
                booked = row.get('booked_seats') or 0
                total = row.get('total_seats') or 1
                pct = (booked / total * 100) if total > 0 else 0
                md += f"| {row.get('line', '-')} | {row.get('origin_station_id')}-{row.get('destination_station_id')} | {booked} | {total} | {pct:.1f}% |\n"
        else:
            md += "*No occupancy data available*\n"
        
        return md
    except Exception as e:
        return f"Error loading operations summary: {str(e)}"


def load_admin_system_stats():
    """Load and format admin system statistics."""
    try:
        data = query_admin_system_stats()
        user_stats = data.get("user_stats", {})
        booking_stats = data.get("booking_stats", {})
        payment_stats = data.get("payment_stats", {})
        
        md = "### System Statistics\n\n"
        md += "#### Users\n"
        md += f"- **Total Users:** {user_stats.get('total_users', 0)}\n"
        md += f"- **Admins:** {user_stats.get('admin_count', 0)}\n"
        md += f"- **Employees:** {user_stats.get('employee_count', 0)}\n"
        md += f"- **Passengers:** {user_stats.get('passenger_count', 0)}\n"
        md += f"- **Active Users:** {user_stats.get('active_users', 0)}\n\n"
        
        md += "#### Bookings\n"
        md += f"- **Total Bookings:** {booking_stats.get('total_bookings', 0)}\n"
        md += f"- **Confirmed:** {booking_stats.get('confirmed', 0)}\n"
        md += f"- **Completed:** {booking_stats.get('completed', 0)}\n"
        md += f"- **Cancelled:** {booking_stats.get('cancelled', 0)}\n"
        md += f"- **Total Revenue:** ${booking_stats.get('total_revenue', 0):.2f}\n"
        md += f"- **Avg Booking Value:** ${booking_stats.get('avg_booking_value', 0):.2f}\n\n"
        
        md += "#### Payments\n"
        md += f"- **Total Payments:** {payment_stats.get('total_payments', 0)}\n"
        md += f"- **Paid:** {payment_stats.get('paid', 0)}\n"
        md += f"- **Refunded:** {payment_stats.get('refunded', 0)}\n"
        md += f"- **Failed:** {payment_stats.get('failed', 0)}\n"
        md += f"- **Total Paid Amount:** ${payment_stats.get('total_paid', 0):.2f}\n"
        
        return md
    except Exception as e:
        return f"Error loading system statistics: {str(e)}"


def load_admin_users():
    """Load and format admin user list."""
    try:
        users = query_admin_all_users()
        
        md = "### All Users\n\n"
        if users:
            md += "| Email | Name | Role | Active | Registered |\n|---|---|---|---|---|\n"
            for user in users:
                name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                active = "✅" if user.get('is_active') else "❌"
                registered = str(user.get('registered_at', ''))[:10]
                md += f"| {user.get('email', '-')} | {name} | {user.get('user_role', '-')} | {active} | {registered} |\n"
        else:
            md += "*No users found*\n"
        
        return md
    except Exception as e:
        return f"Error loading users: {str(e)}"


def load_admin_top_passengers():
    """Load and format admin top passengers."""
    try:
        passengers = query_admin_top_passengers()
        
        md = "### Top 10 Passengers\n\n"
        if passengers:
            md += "| Email | Name | Bookings | Total Spent |\n|---|---|---|---|\n"
            for passenger in passengers:
                name = f"{passenger.get('first_name', '')} {passenger.get('last_name', '')}"
                spent = passenger.get('total_spent') or 0
                md += f"| {passenger.get('email', '-')} | {name} | {passenger.get('booking_count', 0)} | ${spent:.2f} |\n"
        else:
            md += "*No passenger data available*\n"
        
        return md
    except Exception as e:
        return f"Error loading top passengers: {str(e)}"


def load_admin_policies():
    """Load and format admin policies list."""
    try:
        policies = query_admin_policy_list()
        
        md = "### All Policy Documents\n\n"
        if policies:
            md += "| Title | Category | Size | Created |\n|---|---|---|---|\n"
            for policy in policies:
                created = str(policy.get('created_at', ''))[:10] if policy.get('created_at') else '-'
                md += f"| {policy.get('title', '-')} | {policy.get('category', '-')} | {policy.get('content_length', 0)} bytes | {created} |\n"
        else:
            md += "*No policies found*\n"
        
        return md
    except Exception as e:
        return f"Error loading policies: {str(e)}"


def clear_admin_cache():
    """Manually clear the administrator and employee dashboard caches."""
    invalidate_cache("admin:*")
    invalidate_cache("employee:*")
    return "Cache cleared!"


def get_task_status(task_id: str):
    """Retrieve Celery background task status."""
    task = celery_app.AsyncResult(task_id)
    if task.state == 'PENDING':
        return {"status": "Pending...", "progress": 0}
    elif task.state == 'SUCCESS':
        return {"status": "Completed!", "progress": 100, "result": task.result}
    elif task.state == 'FAILURE':
        return {"status": "Failed!", "error": str(task.info)}
    else:
        return {"status": task.state, "progress": 50}


def update_dashboard(current_user: str, user_role: str):
    """Update dashboard visibility and content based on user role."""
    if not current_user or not user_role:
        return (
            gr.update(visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
        )
    
    employee_visible = user_role in ("employee", "admin")
    admin_visible = user_role == "admin"
    
    employee_content = load_employee_operations_summary() if employee_visible else ""
    admin_stats_content = load_admin_system_stats() if admin_visible else ""
    admin_users_content = load_admin_users() if admin_visible else ""
    admin_top_passengers_content = load_admin_top_passengers() if admin_visible else ""
    admin_policies_content = load_admin_policies() if admin_visible else ""
    
    return (
        gr.update(visible=employee_visible),
        gr.update(value=employee_content),
        gr.update(visible=admin_visible),
        gr.update(value=admin_stats_content),
        gr.update(value=admin_users_content),
        gr.update(value=admin_top_passengers_content),
        gr.update(value=admin_policies_content),
    )



# ── Example queries ────────────────────────────────────────────────────────────

EXAMPLES = [
    "What national rail trains run from Central (NR01) to Stonehaven (NR05)?",
    "What is the fastest metro route from MS01 to MS14?",
    "How do I get from Central Square (MS01) to Stonehaven (NR05)?",
    "If Old Town station (NR03) is closed, what alternative routes exist from NR01 to NR05?",
    "My train was delayed 45 minutes — what compensation am I entitled to?",
    "What is the company policy on travelling with a bicycle on national rail?",
]


# ── Build UI ───────────────────────────────────────────────────────────────────

with gr.Blocks(title="TransitFlow") as demo:

    # ── Hidden state ──────────────────────────────────────────────────
    agent_history_state = gr.State([])
    current_user_state  = gr.State(None)   # None = guest, email str = logged in
    current_user_role_state = gr.State(None)  # passenger, employee, admin

    # ── Header: title + auth buttons ─────────────────────────────────
    with gr.Row(equal_height=True):
        gr.Markdown("""
# 🚂 TransitFlow Intelligent Rail Assistant
*Powered by PostgreSQL · pgvector · Neo4j · LLM*
        """)
        with gr.Column(scale=0, min_width=240):
            with gr.Row():
                login_btn    = gr.Button("👤 Login",    size="sm", variant="secondary")
                register_btn = gr.Button("📝 Register", size="sm", variant="secondary")
            user_info_display = gr.Markdown("", visible=False)
            logout_btn = gr.Button("Logout", size="sm", variant="stop", visible=False)

    # ── Login panel (hidden by default) ──────────────────────────────
    with gr.Column(visible=False) as login_panel:
        gr.Markdown("### Login")
        login_email_in    = gr.Textbox(label="Email", placeholder="you@example.com")
        login_password_in = gr.Textbox(label="Password", type="password")
        login_error_msg   = gr.Markdown("", visible=False)
        with gr.Row():
            login_submit_btn = gr.Button("Login", variant="primary")
            forgot_link_btn  = gr.Button("Forgot password?", size="sm")
            login_cancel_btn = gr.Button("Cancel", size="sm")

    # ── Register panel (hidden by default) ───────────────────────────
    with gr.Column(visible=False) as register_panel:
        gr.Markdown("### Create an Account")
        with gr.Row():
            reg_first_name_in = gr.Textbox(label="First name")
            reg_surname_in    = gr.Textbox(label="Surname")
        reg_email_in    = gr.Textbox(label="Email", placeholder="you@example.com")
        reg_year_in     = gr.Textbox(label="Year of birth", placeholder="e.g. 1990")
        reg_password_in = gr.Textbox(label="Password", type="password")
        reg_question_in = gr.Dropdown(choices=SECRET_QUESTIONS, label="Security question")
        reg_answer_in   = gr.Textbox(label="Secret answer")
        reg_identity_key_in = gr.Textbox(
            label="Identity Key (Optional)",
            type="password",
            placeholder="Leave empty for passenger, or enter employee/admin key"
        )
        reg_error_msg   = gr.Markdown("", visible=False)
        with gr.Row():
            reg_submit_btn = gr.Button("Register", variant="primary")
            reg_cancel_btn = gr.Button("Cancel", size="sm")

    # ── Forgot password panel (hidden by default) ─────────────────────
    with gr.Column(visible=False) as forgot_panel:
        gr.Markdown("### Reset Your Password")
        forgot_email_in          = gr.Textbox(label="Email address", placeholder="you@example.com")
        forgot_check_btn         = gr.Button("Find my question", variant="secondary")
        forgot_question_display  = gr.Markdown("", visible=False)
        forgot_answer_in         = gr.Textbox(label="Your answer", visible=False)
        forgot_new_password_in   = gr.Textbox(label="New password", type="password", visible=False)
        forgot_reset_btn         = gr.Button("Reset password", variant="primary", visible=False)
        forgot_msg               = gr.Markdown("")
        forgot_back_btn          = gr.Button("Back to login", size="sm")

    # ── Main chat area ────────────────────────────────────────────────
    with gr.Row():

        # ── Left: chat ────────────────────────────────────────────────
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="TransitFlow Assistant", height=420)

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask e.g. 'Are there seats from London to Bristol?'",
                    show_label=False,
                    scale=4,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            with gr.Row():
                clear_btn    = gr.Button("🗑️ Clear conversation", size="sm")
                debug_toggle = gr.Checkbox(label="🔍 Show database debug panel", value=True)

            # Debug panel — hidden until checkbox is ticked and a message is sent
            debug_panel = gr.Markdown(
                value="",
                visible=False,
            )

        # ── Right: sidebar ────────────────────────────────────────────
        with gr.Column(scale=1):

            gr.Markdown("### 🤖 LLM Provider")
            chat_model_dropdown = gr.Dropdown(
                choices=get_chat_model_choices(),
                value=get_initial_chat_model_value(),
                label="Chat model",
                info="Local Ollama models run fully locally. Gemini uses your API key.",
            )
            provider_status = gr.Markdown(value="**Active:** llama3.2:1b")
            ollama_status   = gr.Markdown(value=get_ollama_status())

            gr.Markdown("---")

            gr.Markdown("### 💡 Try these examples")
            for example in EXAMPLES:
                gr.Button(example, size="sm").click(
                    fn=lambda e=example: e,
                    outputs=msg,
                )

    # ── Employee Dashboard (hidden by default) ──────────────────────────
    with gr.Group(visible=False) as employee_panel:
        gr.Markdown("## 👔 Employee Dashboard")
        
        with gr.Row():
            employee_refresh_btn = gr.Button("🔄 Refresh Operations Data", variant="primary")
        
        with gr.Tabs():
            with gr.Tab("Today's Operations"):
                employee_ops_display = gr.Markdown("Loading...")
            
            with gr.Tab("Station Status"):
                employee_status_display = gr.Markdown("No data")

    # ── Admin Dashboard (hidden by default) ─────────────────────────────
    with gr.Group(visible=False) as admin_panel:
        gr.Markdown("## 🔐 Admin Dashboard")
        
        with gr.Tabs():
            with gr.Tab("System Statistics"):
                admin_stats_display = gr.Markdown("Loading...")
                with gr.Row():
                    admin_stats_refresh_btn = gr.Button("🔄 Refresh", size="sm")
                    admin_clear_cache_btn = gr.Button("🔄 Clear Cache", variant="secondary", size="sm")
            
            with gr.Tab("Users"):
                admin_users_display = gr.Markdown("Loading...")
                admin_users_refresh_btn = gr.Button("🔄 Refresh", size="sm")
            
            with gr.Tab("Top Passengers"):
                admin_top_passengers_display = gr.Markdown("Loading...")
                admin_top_passengers_refresh_btn = gr.Button("🔄 Refresh", size="sm")
            
            with gr.Tab("Policies"):
                admin_policies_display = gr.Markdown("Loading...")
                admin_policies_refresh_btn = gr.Button("🔄 Refresh", size="sm")

            with gr.Tab("Task Progress"):
                gr.Markdown("### ⚙️ Celery Task Tracker")
                task_id_input = gr.Textbox(label="Enter Celery Task ID")
                check_task_btn = gr.Button("🔍 Check Task Status", variant="primary")
                task_status_display = gr.Markdown("", visible=False)

    # ── Event wiring ──────────────────────────────────────────────────

    chat_model_dropdown.change(
        fn=on_chat_model_change,
        inputs=chat_model_dropdown,
        outputs=[provider_status, ollama_status],
    )

    send_btn.click(
        fn=chat,
        inputs=[msg, chatbot, agent_history_state, debug_toggle, current_user_state],
        outputs=[chatbot, agent_history_state, debug_panel],
    ).then(fn=lambda: "", outputs=msg)

    msg.submit(
        fn=chat,
        inputs=[msg, chatbot, agent_history_state, debug_toggle, current_user_state],
        outputs=[chatbot, agent_history_state, debug_panel],
    ).then(fn=lambda: "", outputs=msg)

    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot, agent_history_state, debug_panel],
    )

    # Panel toggle buttons
    login_btn.click(
        fn=show_login_panel,
        outputs=[login_panel, register_panel, forgot_panel],
    )
    register_btn.click(
        fn=show_register_panel,
        outputs=[login_panel, register_panel, forgot_panel],
    )
    login_cancel_btn.click(
        fn=hide_all_panels,
        outputs=[login_panel, register_panel, forgot_panel],
    )
    reg_cancel_btn.click(
        fn=hide_all_panels,
        outputs=[login_panel, register_panel, forgot_panel],
    )
    forgot_link_btn.click(
        fn=show_forgot_panel,
        outputs=[login_panel, register_panel, forgot_panel],
    )
    forgot_back_btn.click(
        fn=show_login_panel,
        outputs=[login_panel, register_panel, forgot_panel],
    )

    # Login
    login_submit_btn.click(
        fn=do_login,
        inputs=[login_email_in, login_password_in],
        outputs=[
            login_error_msg,
            current_user_state,
            current_user_role_state,
            login_btn,
            register_btn,
            user_info_display,
            logout_btn,
            login_panel,
        ],
    ).then(
        fn=update_dashboard,
        inputs=[current_user_state, current_user_role_state],
        outputs=[
            employee_panel,
            employee_ops_display,
            admin_panel,
            admin_stats_display,
            admin_users_display,
            admin_top_passengers_display,
            admin_policies_display,
        ],
    )

    # Logout
    logout_btn.click(
        fn=do_logout,
        outputs=[
            current_user_state,
            current_user_role_state,
            login_btn,
            register_btn,
            user_info_display,
            logout_btn,
            login_panel,
            register_panel,
            forgot_panel,
        ],
    ).then(
        fn=update_dashboard,
        inputs=[current_user_state, current_user_role_state],
        outputs=[
            employee_panel,
            employee_ops_display,
            admin_panel,
            admin_stats_display,
            admin_users_display,
            admin_top_passengers_display,
            admin_policies_display,
        ],
    )

    # Register
    reg_submit_btn.click(
        fn=do_register,
        inputs=[
            reg_email_in, reg_first_name_in, reg_surname_in,
            reg_year_in, reg_password_in, reg_question_in, reg_answer_in,
            reg_identity_key_in,
        ],
        outputs=[
            reg_error_msg,
            current_user_state,
            current_user_role_state,
            login_btn,
            register_btn,
            user_info_display,
            logout_btn,
            register_panel,
        ],
    ).then(
        fn=update_dashboard,
        inputs=[current_user_state, current_user_role_state],
        outputs=[
            employee_panel,
            employee_ops_display,
            admin_panel,
            admin_stats_display,
            admin_users_display,
            admin_top_passengers_display,
            admin_policies_display,
        ],
    )

    # Forgot password — step 1: find question
    forgot_check_btn.click(
        fn=forgot_find_question,
        inputs=[forgot_email_in],
        outputs=[
            forgot_msg,
            forgot_question_display,
            forgot_answer_in,
            forgot_new_password_in,
            forgot_reset_btn,
        ],
    )

    # Forgot password — step 2: reset
    forgot_reset_btn.click(
        fn=forgot_reset_password,
        inputs=[forgot_email_in, forgot_answer_in, forgot_new_password_in],
        outputs=[forgot_msg],
    )

    # Employee dashboard refresh
    employee_refresh_btn.click(
        fn=load_employee_operations_summary,
        outputs=[employee_ops_display],
    )

    # Admin dashboard refreshes
    admin_stats_refresh_btn.click(
        fn=load_admin_system_stats,
        outputs=[admin_stats_display],
    )

    admin_clear_cache_btn.click(
        fn=clear_admin_cache,
        outputs=[admin_stats_display],
    ).then(
        fn=load_admin_system_stats,
        outputs=[admin_stats_display],
    )

    admin_users_refresh_btn.click(
        fn=load_admin_users,
        outputs=[admin_users_display],
    )

    admin_top_passengers_refresh_btn.click(
        fn=load_admin_top_passengers,
        outputs=[admin_top_passengers_display],
    )

    admin_policies_refresh_btn.click(
        fn=load_admin_policies,
        outputs=[admin_policies_display],
    )

    def check_report_progress(task_id: str):
        if not task_id.strip():
            return gr.update(value="⚠️ Please enter a task ID.", visible=True)
        status = get_task_status(task_id.strip())
        val = f"**Status:** {status['status']} ({status['progress']}%)\n"
        if "result" in status:
            val += f"\n**Result:**\n```json\n{status['result']}\n```"
        elif "error" in status:
            val += f"\n**Error:** {status['error']}"
        return gr.update(value=val, visible=True)

    check_task_btn.click(
        fn=check_report_progress,
        inputs=[task_id_input],
        outputs=[task_status_display]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
    )
