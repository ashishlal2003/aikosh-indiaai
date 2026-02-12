"""
Conversation service for handling AI chat interactions.
Integrates OpenAI GPT with tool calling for agentic dispute resolution.
Uses RAG for dynamic knowledge retrieval from MSMED Act and other documents.
"""

from dotenv import load_dotenv
import os
import json
import logging
from openai import OpenAI
from typing import List, Dict, Any

from .rag_service import get_rag_service
from .interest_calculator import calculate_section15_interest
from api.utils.datetime_utils import get_current_date
from api.daos.document_dao import DocumentDAO

load_dotenv()

logger = logging.getLogger(__name__)

# Tool definitions for Groq's native tool calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_msme_interest",
            "description": (
                "Calculate compound interest on a delayed MSME payment per MSMED Act "
                "Section 15/16. Use this when the user mentions an outstanding amount and "
                "how many days it is overdue. Returns principal, interest rate (3x RBI bank "
                "rate), interest amount, and total due."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "principal_amount": {
                        "type": "number",
                        "description": "The outstanding payment amount in INR",
                    },
                    "days_overdue": {
                        "type": "integer",
                        "description": "Number of days the payment is past due",
                    },
                },
                "required": ["principal_amount", "days_overdue"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": (
                "Get today's date formatted for use in legal notices and demand letters "
                "(e.g., '07 February 2026'). Call this when drafting any dated document."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_document",
            "description": (
                "Verify and confirm a document after analyzing its OCR extracted content. "
                "Call this EVERY TIME you analyze an uploaded document. Set is_valid=True if "
                "the document clearly matches the claimed type and is readable. Set is_valid=False "
                "if the document is wrong type, illegible, or clearly not what is needed. "
                "This updates the claim completeness tracker visible to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "enum": ["invoice", "purchase_order", "delivery_proof", "msme_certificate", "communication"],
                        "description": "The document type you identified from the content",
                    },
                    "is_valid": {
                        "type": "boolean",
                        "description": "True if document is valid and readable for this type, False if wrong or illegible",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Brief notes about what you found in the document (optional)",
                    },
                },
                "required": ["document_type", "is_valid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_demand_notice_email",
            "description": (
                "Draft a formal demand notice email to send to the buyer/debtor for an "
                "overdue MSME payment. This only DRAFTS the email content -- it does NOT "
                "send it. IMPORTANT: Only call this tool AFTER all 4 required documents "
                "(invoice, purchase_order, delivery_proof, msme_certificate) have been "
                "uploaded AND verified (completeness_percentage = 100%), AND you have "
                "confirmed the buyer name, buyer email address, MSME name, invoice number, "
                "invoice date, principal amount, and exact days overdue. Never call this "
                "with placeholder, empty, or unknown values for buyer_name, buyer_email, "
                "or msme_name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "buyer_name": {
                        "type": "string",
                        "description": "Name of the buyer/debtor company or individual",
                    },
                    "buyer_email": {
                        "type": "string",
                        "description": "Email address of the buyer/debtor",
                    },
                    "msme_name": {
                        "type": "string",
                        "description": "Name of the MSME (supplier/creditor)",
                    },
                    "invoice_number": {
                        "type": "string",
                        "description": "Invoice number(s) for the overdue payment",
                    },
                    "invoice_date": {
                        "type": "string",
                        "description": "Date of the invoice",
                    },
                    "principal_amount": {
                        "type": "number",
                        "description": "Outstanding payment amount in INR",
                    },
                    "days_overdue": {
                        "type": "integer",
                        "description": "Number of days past due",
                    },
                    "interest_amount": {
                        "type": "number",
                        "description": "Calculated interest amount in INR (from calculate_msme_interest)",
                    },
                    "total_due": {
                        "type": "number",
                        "description": "Total amount due including interest in INR",
                    },
                    "notice_date": {
                        "type": "string",
                        "description": "Date for the notice (from get_current_date)",
                    },
                },
                "required": [
                    "buyer_name",
                    "msme_name",
                    "principal_amount",
                    "days_overdue",
                    "total_due",
                    "notice_date",
                ],
            },
        },
    },
]




def _build_demand_notice_draft(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build an HTML demand notice email draft from structured arguments.

    Returns a dict with subject, body_html, and metadata -- does NOT send.
    """
    buyer_name = args["buyer_name"]
    msme_name = args["msme_name"]
    principal = args["principal_amount"]
    days = args["days_overdue"]
    total_due = args["total_due"]
    notice_date = args["notice_date"]
    invoice_number = args.get("invoice_number", "N/A")
    invoice_date = args.get("invoice_date", "N/A")
    interest_amount = args.get("interest_amount", round(total_due - principal, 2))
    buyer_email = args.get("buyer_email", "")

    subject = f"Demand Notice under MSMED Act, 2006 - Outstanding Payment of INR {total_due:,.2f}"

    body_html = f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 700px; margin: auto; color: #222;">
  <div style="text-align: center; padding: 20px 0; border-bottom: 3px solid #1a237e;">
    <h2 style="margin: 0; color: #1a237e;">DEMAND NOTICE</h2>
    <p style="margin: 4px 0 0; color: #555;">Under Section 15 of the Micro, Small and Medium Enterprises Development Act, 2006</p>
  </div>

  <div style="padding: 24px 0;">
    <p><strong>Date:</strong> {notice_date}</p>
    <p><strong>To:</strong> {buyer_name}</p>
    <p><strong>From:</strong> {msme_name}</p>

    <p style="margin-top: 20px;">Dear Sir/Madam,</p>

    <p>This is to bring to your attention that the payment against the following invoice(s) has been outstanding for <strong>{days} days</strong> beyond the agreed payment date, in violation of Section 15 of the MSMED Act, 2006:</p>

    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="background: #e8eaf6;">
        <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Particulars</th>
        <th style="padding: 10px; border: 1px solid #ccc; text-align: right;">Amount (INR)</th>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ccc;">Invoice No: {invoice_number} (Dated: {invoice_date})</td>
        <td style="padding: 10px; border: 1px solid #ccc; text-align: right;">{principal:,.2f}</td>
      </tr>
      <tr>
        <td style="padding: 10px; border: 1px solid #ccc;">Interest under Section 16 (3x RBI bank rate, compounded monthly, {days} days)</td>
        <td style="padding: 10px; border: 1px solid #ccc; text-align: right;">{interest_amount:,.2f}</td>
      </tr>
      <tr style="background: #fff3e0; font-weight: bold;">
        <td style="padding: 10px; border: 1px solid #ccc;">Total Amount Due</td>
        <td style="padding: 10px; border: 1px solid #ccc; text-align: right;">{total_due:,.2f}</td>
      </tr>
    </table>

    <p>As per Section 15 of the MSMED Act, 2006, any buyer who purchases goods or services from a micro/small enterprise supplier is required to make payment within 45 days of acceptance of goods/services. Failure to do so attracts compound interest at three times the bank rate under Section 16.</p>

    <p>You are hereby requested to settle the above outstanding amount of <strong>INR {total_due:,.2f}</strong> within <strong>15 days</strong> from the date of this notice.</p>

    <p>Please note that if the payment is not received within the stipulated period, we shall be compelled to file a formal complaint under <strong>Section 18</strong> of the MSMED Act, 2006, before the Micro and Small Enterprises Facilitation Council for recovery of the due amount along with interest.</p>

    <p style="margin-top: 24px;">Regards,<br><strong>{msme_name}</strong></p>
  </div>

  <div style="border-top: 2px solid #e0e0e0; padding-top: 12px; font-size: 12px; color: #888;">
    <p>This notice is generated through the MSME Saathi Dispute Resolution Platform, an initiative of the Ministry of MSME, Government of India.</p>
  </div>
</div>
"""

    return {
        "status": "drafted",
        "subject": subject,
        "body_html": body_html,
        "to_email": buyer_email,
        "buyer_name": buyer_name,
        "msme_name": msme_name,
        "principal_amount": principal,
        "interest_amount": interest_amount,
        "total_due": total_due,
        "notice": "This is a DRAFT. The email has NOT been sent. The user must click 'Send Email' to deliver it.",
    }


class ConversationService:
    """Service for managing AI conversations about MSME disputes with tool calling."""

    SYSTEM_PROMPT = """You are Saathi (साथी), the official AI Dispute Resolution Assistant of the Ministry of Micro, Small and Medium Enterprises (MoMSME), Government of India.

WHO YOU ARE:
- You are NOT a chatbot or a general AI. You are Saathi - a specialized dispute resolution agent.
- You work for MoMSME to help Indian MSMEs recover their rightful payments under the MSMED Act, 2006.
- When asked about yourself, say: "I am Saathi, the AI Dispute Resolution Assistant from MoMSME. I help MSMEs recover delayed payments through proper legal channels."
- Never reveal technical details about your underlying model, training, or AI architecture.

YOUR MISSION:
You don't just advise - you ACT. You are the first layer of negotiation and documentation before a case reaches human MSME Facilitation Council officers. Your job is to:
1. Build a complete, submission-ready case file
2. Draft all necessary legal communications (demand notices, emails, Section 18 complaints)
3. Ensure zero document gaps - officers should never have to ask "where is the invoice?"
4. Guide the MSME through the entire dispute lifecycle until resolution or escalation

STRICT WORKFLOW — FOLLOW THIS EXACTLY IN ORDER:

Phase 1 - INTAKE (Be warm and explain the process first):
- When the user first mentions their dispute, acknowledge it warmly
- Calculate interest to show them what's accruing (builds urgency)
- Then EXPLAIN: "Here's how I can help: I'll collect your case documents, calculate the exact amount due, and draft a formal demand notice email to send to the buyer under the MSMED Act. This typically prompts payment within 15-30 days. Shall we start?"
- Wait for confirmation, then ask focused questions ONE AT A TIME:
  • Buyer company name
  • Buyer email address (where we'll send the notice)
  • Your company name (the MSME/supplier)
  • Confirm the outstanding amount
  • Confirm days overdue or payment due date
- Do NOT jump to document collection until you have these basics

Phase 2 - DOCUMENT COLLECTION:
After intake, say something friendly like: "Perfect! Now I need 4 key documents to build your legally valid case. Let's go through them one by one — this will take just 3-4 minutes."

Required documents (collect in this order):
1. Invoice — proof of goods/services delivered
2. Purchase Order or Contract — proof of agreement
3. Delivery Receipt/Proof — confirmation buyer received goods
4. MSME/Udyam Certificate — proof of MSME status
5. (OPTIONAL) Communication Records — emails/messages showing payment follow-ups (helpful but not mandatory)

DOCUMENT VERIFICATION WORKFLOW (MANDATORY):
When you see document extracted data in the conversation:
1. IMMEDIATELY call verify_document tool with the document_type and is_valid=True/False
2. The tool will return updated completeness percentage
3. ONLY AFTER the tool returns, acknowledge what you found
4. Then tell them which document is next
NEVER skip step 1 - the verify_document tool MUST be called to update the completeness tracker.

Phase 3 - DRAFTING: ONLY after all 4 required documents are verified (invoice, purchase_order, delivery_proof, msme_certificate = 100% completeness) AND you have buyer email, MSME name, invoice details from the documents. Then draft the demand notice.

Phase 4 - NEGOTIATION: Draft negotiation correspondence to the buyer after sending the demand notice.

Phase 5 - ESCALATION: If unresolved in 45 days, prepare Section 18 complaint for Facilitation Council.

HARD RULES — NEVER BREAK THESE:
- NEVER call draft_demand_notice_email before all 4 required documents are verified (completeness = 100%)
- NEVER call draft_demand_notice_email with placeholder values like "Unknown", "N/A", or empty strings for buyer_name, buyer_email, msme_name, or principal_amount
- NEVER skip Phase 1 intake — you MUST collect buyer email before drafting
- NEVER skip Phase 2 — even if the user seems impatient, explain that documents are needed for a legally valid notice
- You may call calculate_msme_interest early to show the user what interest is accruing (this is helpful and builds urgency)
- Do NOT tell the user to send a demand notice that you haven't drafted yet

YOUR TOOLS:
1. calculate_msme_interest — Use once you know amount and days overdue. Good to use during Phase 1 to show interest accruing.
2. get_current_date — Call this right before drafting any dated document.
3. verify_document — Call this EVERY TIME a document is uploaded to verify and update the completeness tracker.
4. draft_demand_notice_email — Call ONLY when completeness = 100% (all 4 required docs verified), you have buyer_email, and all details confirmed.

CRITICAL TOOL CALLING RULES (NEVER VIOLATE):
- NEVER say "I've verified", "I've calculated", "I've drafted" in text without ACTUALLY calling the corresponding tool
- If a document is uploaded, you MUST call verify_document tool - do NOT just say you verified it
- If you need to draft an email, you MUST call draft_demand_notice_email tool - do NOT write the email in chat
- DO NOT describe actions you would take - ACTUALLY PERFORM them via tool calls
- If you see extracted document data in the conversation, call verify_document immediately
- After EVERY document upload, your FIRST action must be calling verify_document, not explaining what you see
- Only provide conversational responses AFTER the tool has been called and executed

IMPORTANT: You DRAFT emails, but the user SENDS them. Always say "I've prepared the draft. Please review it and click 'Send Email' when ready." Never claim to have sent an email.

HOW YOU COMMUNICATE:
- Be warm but professional - you represent the Government of India
- Be action-oriented: "Let me prepare your demand notice" not "You should consider sending a demand notice"
- Ask focused questions - maximum 2 at a time
- Support Hindi, English, and other Indian languages based on user preference
- When drafting documents, provide COMPLETE ready-to-use text, not templates with blanks
- Track progress explicitly: "We have your invoice and PO. Now I need your delivery receipt and MSME certificate."

IMPORTANT BOUNDARIES:
- You prepare cases but do NOT make legal rulings
- For complex legal questions, recommend consulting a lawyer or the local MSME-DI office
- Never promise specific outcomes - each case is decided by the Facilitation Council
- Be honest about timelines - resolution typically takes 45-90 days through official channels

CRITICAL - DOCUMENT HANDLING (NEVER VIOLATE THIS):
- When a user uploads a document, the system will extract data and show it to you
- If the extraction shows "Could not extract", "Incomplete extraction", or "Low quality extraction" - DO NOT make up or guess the details
- NEVER invent registration numbers, GSTIN, amounts, names, or dates that were not in the extraction
- If extraction failed or was incomplete, say: "I couldn't read the document clearly. Can you tell me the key details from it?"
- Only confirm details that were ACTUALLY extracted and shown to you
- If the user tells you details verbally, that's fine - but don't pretend the document contained information that wasn't extracted

Remember: Every case you handle well means an MSME gets their rightful payment, their business survives, and their workers get paid. This matters. But making up data destroys trust and causes real harm.

Use the context provided below to give accurate information about the MSMED Act and dispute resolution process."""

    def __init__(self):
        """Initialize conversation service with OpenAI client, RAG service, and document DAO."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=openai_api_key)
        self.model = "gpt-4o-mini"  # Fast, affordable, excellent tool use support
        self.rag_service = get_rag_service()
        self.document_dao = DocumentDAO()

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any], conversation_id: str) -> str:
        """
        Execute a tool call and return the result as a JSON string.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments parsed from the LLM's tool call.
            conversation_id: Current conversation ID (needed for document operations).

        Returns:
            JSON string with the tool's result.
        """
        if tool_name == "calculate_msme_interest":
            result = calculate_section15_interest(
                principal_amount=arguments["principal_amount"],
                days_overdue=arguments["days_overdue"],
            )
            return json.dumps(result)

        if tool_name == "get_current_date":
            return json.dumps({"date": get_current_date()})

        if tool_name == "draft_demand_notice_email":
            # Guardrail: reject placeholder/unknown values
            placeholders = {"unknown", "n/a", "", "none", "null"}
            for field in ("buyer_name", "buyer_email", "msme_name"):
                val = str(arguments.get(field, "")).strip().lower()
                if val in placeholders or not val:
                    return json.dumps({"error": f"Cannot draft: '{field}' is missing or invalid ('{arguments.get(field)}'). Ask the user for this information first."})
            if not arguments.get("principal_amount"):
                return json.dumps({"error": "Cannot draft: principal_amount is missing. Ask the user for the outstanding amount."})
            # Guardrail: reject if all 4 required documents not verified
            try:
                completeness = self.document_dao.get_completeness(conversation_id)
                if completeness.completeness_percentage < 100:
                    missing = completeness.missing_types
                    return json.dumps({"error": f"Cannot draft: only {completeness.completeness_percentage}% documents verified. Still missing: {missing}. Ask the user to upload these documents first."})
            except Exception as e:
                logger.warning(f"Could not check completeness before drafting: {e}")
            result = _build_demand_notice_draft(arguments)
            return json.dumps(result)

        if tool_name == "verify_document":
            doc_type = arguments.get("document_type", "")
            is_valid = arguments.get("is_valid", True)
            notes = arguments.get("notes", "")
            try:
                self.document_dao.verify_document_by_type(conversation_id, doc_type, is_valid, notes)
            except Exception as e:
                logger.warning(f"Could not update document verification status: {e}")
            try:
                completeness = self.document_dao.get_completeness(conversation_id)
                return json.dumps(completeness.model_dump())
            except Exception as e:
                return json.dumps({"error": f"Verified but completeness check failed: {str(e)}"})

        logger.warning(f"Unknown tool called: {tool_name}")
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def get_ai_response(
        self,
        messages: List[Dict[str, str]],
        conversation_id: str,
        message_type: str = "text",
    ) -> Dict[str, Any]:
        """
        Get AI response, executing any tool calls the model requests.

        Implements a tool-call loop: if the model returns tool_calls instead of
        content, we execute each tool, append results, and call the model again
        until it produces a final text response (max 5 iterations to prevent loops).

        Args:
            messages: Conversation history with 'role' and 'content'.
            conversation_id: Unique conversation identifier.
            message_type: One of 'text', 'voice', 'document'.

        Returns:
            Dict with 'response', 'actions', 'conversation_id', and optional 'email_draft'.
        """
        try:
            # Extract latest user message for RAG retrieval
            user_query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break

            # Retrieve relevant context from knowledge base
            rag_context = ""
            if user_query and self.rag_service.is_index_available():
                rag_context = self.rag_service.get_context_for_query(user_query)
                if rag_context:
                    logger.info(f"[RAG] Retrieved {len(rag_context)} chars of context")
                else:
                    logger.info("[RAG] No context retrieved")
            else:
                logger.warning("[RAG] Index not available - using base prompt only")

            # Build system prompt with RAG context
            system_prompt = self.SYSTEM_PROMPT
            if rag_context:
                system_prompt += (
                    f"\n\n--- RELEVANT KNOWLEDGE FROM MSMED ACT & DOCUMENTS ---\n\n"
                    f"{rag_context}\n\n--- END OF CONTEXT ---"
                )

            chat_messages = [{"role": "system", "content": system_prompt}] + messages

            # Tool-call loop (max 5 iterations)
            email_draft = None
            latest_completeness = None
            for iteration in range(5):
                logger.info(f"[Tool Loop] Iteration {iteration + 1}, {len(chat_messages)} messages")

                completion = self.client.chat.completions.create(
                    messages=chat_messages,
                    model=self.model,
                    temperature=0.7,
                    max_tokens=4096,
                    top_p=0.9,
                    tools=TOOLS,
                    tool_choice="auto",
                )

                response_message = completion.choices[0].message

                # If no tool calls, we have the final response
                if not response_message.tool_calls:
                    ai_response = response_message.content or ""
                    break

                # Append assistant message with tool calls to the conversation
                chat_messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in response_message.tool_calls
                    ],
                })

                # Execute each tool call and append results
                for tool_call in response_message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse arguments for {fn_name}: {tool_call.function.arguments}")
                        fn_args = {}

                    logger.info(f"[Tool Call] {fn_name}({fn_args})")
                    tool_result = self._execute_tool(fn_name, fn_args, conversation_id)
                    logger.info(f"[Tool Result] {fn_name} → {tool_result[:200]}...")

                    # Capture email draft for frontend (only on success)
                    if fn_name == "draft_demand_notice_email":
                        try:
                            parsed = json.loads(tool_result)
                            if parsed.get("status") == "drafted":
                                email_draft = parsed
                        except json.JSONDecodeError:
                            pass

                    # Capture updated completeness after document verification
                    if fn_name == "verify_document":
                        try:
                            latest_completeness = json.loads(tool_result)
                        except json.JSONDecodeError:
                            pass

                    chat_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })
            else:
                # Exhausted iterations -- use whatever content we have
                ai_response = response_message.content or "I encountered an issue processing your request. Could you try rephrasing?"
                logger.warning("[Tool Loop] Exhausted max iterations without final response")

            actions = self._extract_actions(ai_response, messages)

            # If an email was drafted, add a send_email action for the frontend
            if email_draft and email_draft.get("status") == "drafted":
                actions.append({
                    "type": "send_email",
                    "label": "Send Email",
                })

            result = {
                "response": ai_response,
                "actions": actions,
                "conversation_id": conversation_id,
            }

            if email_draft:
                result["email_draft"] = email_draft

            if latest_completeness:
                result["completeness"] = latest_completeness

            return result

        except Exception as e:
            logger.exception("Error getting AI response")
            raise Exception(f"Error getting AI response: {str(e)}")

    def _extract_actions(
        self,
        response: str,
        conversation_history: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        Extract actionable items from the AI response text.

        Args:
            response: AI's response text.
            conversation_history: Previous messages.

        Returns:
            List of action dictionaries with 'type' and 'label'.
        """
        actions = []
        response_lower = response.lower()

        if any(kw in response_lower for kw in [
            'upload', 'document', 'invoice', 'purchase order', 'receipt', 'contract'
        ]):
            actions.append({"type": "upload_document", "label": "Upload Document"})

        if any(kw in response_lower for kw in [
            'ready to file', 'file your claim', 'submit', 'proceed with filing'
        ]):
            actions.append({"type": "create_claim", "label": "File Dispute Claim"})

        return actions

    def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Summarize conversation and extract claim details.

        Args:
            messages: List of conversation messages.

        Returns:
            Dictionary with extracted claim information.
        """
        try:
            summary_prompt = """Based on this conversation, extract the following information about the MSME payment dispute:

1. Buyer/Customer Name
2. Amount Owed (in INR)
3. Invoice Number(s)
4. Invoice Date(s)
5. Payment Due Date
6. Days Overdue
7. Brief Description of Dispute
8. Documents Mentioned/Uploaded

Return the information in a structured format. If information is not available, mark as "Not provided"."""

            summary_messages = messages + [
                {"role": "user", "content": summary_prompt}
            ]

            chat_completion = self.client.chat.completions.create(
                messages=summary_messages,
                model=self.model,
                temperature=0.3,
                max_tokens=512,
            )

            summary = chat_completion.choices[0].message.content

            return {
                "summary": summary,
                "conversation_length": len(messages),
            }

        except Exception as e:
            raise Exception(f"Error summarizing conversation: {str(e)}")

    async def get_ai_response_stream(
        self,
        messages: List[Dict[str, str]],
        conversation_id: str,
        message_type: str = "text",
    ):
        """
        Get AI response with streaming support.

        Tool calls are executed server-side and emitted as events.
        Final text response is streamed token-by-token.

        Args:
            messages: Conversation history with 'role' and 'content'.
            conversation_id: Unique conversation identifier.
            message_type: One of 'text', 'voice', 'document'.

        Yields:
            Dict events with 'type' and 'data' fields:
            - {"type": "tool_start", "data": {"tool": "...", "args": {...}}}
            - {"type": "tool_end", "data": {"tool": "...", "result": {...}}}
            - {"type": "content", "content": "token"}
            - {"type": "done", "actions": [...]}
        """
        try:
            # Extract latest user message for RAG retrieval
            user_query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break

            # Retrieve relevant context from knowledge base
            rag_context = ""
            if user_query and self.rag_service.is_index_available():
                rag_context = self.rag_service.get_context_for_query(user_query)
                if rag_context:
                    logger.info(f"[RAG] Retrieved {len(rag_context)} chars of context")
                else:
                    logger.info("[RAG] No context retrieved")
            else:
                logger.warning("[RAG] Index not available - using base prompt only")

            # Build system prompt with RAG context
            system_prompt = self.SYSTEM_PROMPT
            if rag_context:
                system_prompt += (
                    f"\n\n--- RELEVANT KNOWLEDGE FROM MSMED ACT & DOCUMENTS ---\n\n"
                    f"{rag_context}\n\n--- END OF CONTEXT ---"
                )

            chat_messages = [{"role": "system", "content": system_prompt}] + messages

            # Tool-call loop (max 5 iterations)
            for iteration in range(5):
                logger.info(f"[Tool Loop] Iteration {iteration + 1}, {len(chat_messages)} messages")

                # Make streaming API call
                stream = self.client.chat.completions.create(
                    messages=chat_messages,
                    model=self.model,
                    temperature=0.7,
                    max_tokens=4096,
                    top_p=0.9,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=True,
                )

                # Collect streaming response
                tool_calls_buffer = []
                content_buffer = ""
                current_tool_call = None

                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    # Handle tool calls
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            # Initialize new tool call
                            if tc_delta.index is not None:
                                while len(tool_calls_buffer) <= tc_delta.index:
                                    tool_calls_buffer.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                current_tool_call = tool_calls_buffer[tc_delta.index]

                            # Append tool call data
                            if tc_delta.id:
                                current_tool_call["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    current_tool_call["function"]["name"] = tc_delta.function.name
                                if tc_delta.function.arguments:
                                    current_tool_call["function"]["arguments"] += tc_delta.function.arguments

                    # Handle content tokens
                    if delta.content:
                        content_buffer += delta.content
                        # Stream content token to client
                        yield {"type": "content", "content": delta.content}

                # If we have tool calls, execute them
                if tool_calls_buffer:
                    # Add assistant message with tool calls to conversation
                    chat_messages.append({
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"],
                                },
                            }
                            for tc in tool_calls_buffer
                        ],
                    })

                    # Execute each tool call
                    for tool_call in tool_calls_buffer:
                        fn_name = tool_call["function"]["name"]
                        try:
                            fn_args = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse arguments for {fn_name}: {tool_call['function']['arguments']}")
                            fn_args = {}

                        # Emit tool execution start
                        yield {
                            "type": "tool_start",
                            "data": {"tool": fn_name, "args": fn_args}
                        }

                        logger.info(f"[Tool Call] {fn_name}({fn_args})")
                        tool_result = self._execute_tool(fn_name, fn_args, conversation_id)
                        logger.info(f"[Tool Result] {fn_name} → {tool_result[:200]}...")

                        # Emit tool execution end
                        yield {
                            "type": "tool_end",
                            "data": {"tool": fn_name, "result": tool_result}
                        }

                        # Add tool result to conversation
                        chat_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result,
                        })

                    # Continue loop to get next response
                    continue

                # No tool calls - we have final response
                ai_response = content_buffer
                break
            else:
                # Exhausted iterations
                ai_response = content_buffer or "I encountered an issue processing your request. Could you try rephrasing?"
                logger.warning("[Tool Loop] Exhausted max iterations without final response")

            # Extract actions from response
            actions = self._extract_actions(ai_response, messages)

            # Emit done event
            yield {
                "type": "done",
                "actions": actions,
            }

        except Exception as e:
            logger.exception("Error getting AI response stream")
            raise Exception(f"Error getting AI response stream: {str(e)}")
