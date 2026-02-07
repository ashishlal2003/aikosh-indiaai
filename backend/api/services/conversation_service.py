"""
Conversation service for handling AI chat interactions.
Integrates Groq LLM for conversational dispute resolution assistance.
Uses RAG for dynamic knowledge retrieval from MSMED Act and other documents.
"""

from dotenv import load_dotenv
import os
import logging
from groq import Groq
from typing import List, Dict

from .rag_service import get_rag_service

load_dotenv()

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing AI conversations about MSME disputes."""

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

WORKFLOW YOU FOLLOW:
Phase 1 - INTAKE: Understand the dispute (buyer details, amount, timeline, attempts made)
Phase 2 - DOCUMENTATION: Collect all required documents (Invoice, PO, Delivery Proof, MSME Certificate, Communication records)
Phase 3 - DRAFTING: Prepare demand notice, follow-up emails, legal notice if needed
Phase 4 - NEGOTIATION: Draft negotiation correspondence to the buyer
Phase 5 - ESCALATION: If unresolved in 45 days, prepare Section 18 complaint for Facilitation Council

REQUIRED DOCUMENTS (You must collect these):
1. Invoice(s) - proof of goods/services delivered
2. Purchase Order or Contract - proof of agreement
3. Delivery Receipt/Proof - confirmation buyer received goods
4. MSME/Udyam Certificate - proof of MSME status
5. Communication Records - emails/messages showing payment follow-ups
Optional: Bank statements, Legal notices already sent

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

Example of WRONG behavior (never do this):
User: [uploads blurry Udyam certificate with failed extraction]
You: "I see your Udyam number is UDYAM-GJ-01-1234567..." ← WRONG! You made this up.

Example of CORRECT behavior:
User: [uploads blurry Udyam certificate with failed extraction]
You: "I couldn't read the certificate clearly. What is your Udyam Registration Number?" ← CORRECT!

Remember: Every case you handle well means an MSME gets their rightful payment, their business survives, and their workers get paid. This matters. But making up data destroys trust and causes real harm.

Use the context provided below to give accurate information about the MSMED Act and dispute resolution process."""

    def __init__(self):
        """Initialize conversation service with Groq client and RAG service."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=self.groq_api_key)
        self.model = "llama-3.1-8b-instant"
        self.rag_service = get_rag_service()

    def get_ai_response(
        self,
        messages: List[Dict[str, str]],
        conversation_id: str,
        message_type: str = "text"
    ) -> Dict[str, any]:
        """
        Get AI response for the conversation.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            conversation_id: Unique identifier for the conversation
            message_type: Type of message ('text', 'voice', 'document')

        Returns:
            Dictionary with 'response' and optional 'actions'
        """
        try:
            # Get latest user message for RAG query
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
                    logger.info(f"[RAG] Retrieved {len(rag_context)} chars of context for query: '{user_query[:50]}...'")
                else:
                    logger.info(f"[RAG] No context retrieved for query: '{user_query[:50]}...'")
            else:
                logger.warning("[RAG] Index not available - using base prompt only")

            # Build system prompt with RAG context
            system_prompt = self.SYSTEM_PROMPT
            if rag_context:
                system_prompt += f"\n\n--- RELEVANT KNOWLEDGE FROM MSMED ACT & DOCUMENTS ---\n\n{rag_context}\n\n--- END OF CONTEXT ---"

            # Prepare messages with system prompt
            chat_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages

            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=chat_messages,
                model=self.model,
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
            )

            ai_response = chat_completion.choices[0].message.content

            # Analyze response for potential actions
            actions = self._extract_actions(ai_response, messages)

            return {
                "response": ai_response,
                "actions": actions,
                "conversation_id": conversation_id
            }

        except Exception as e:
            raise Exception(f"Error getting AI response: {str(e)}")

    def _extract_actions(
        self,
        response: str,
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Extract actionable items from AI response.

        Args:
            response: AI's response text
            conversation_history: Previous messages

        Returns:
            List of action dictionaries
        """
        actions = []

        response_lower = response.lower()

        # Check if AI is asking for documents
        if any(keyword in response_lower for keyword in [
            'upload', 'document', 'invoice', 'purchase order', 'receipt', 'contract'
        ]):
            actions.append({
                "type": "upload_document",
                "label": "Upload Document"
            })

        # Check if AI is ready to draft email
        if any(keyword in response_lower for keyword in [
            'draft', 'email', 'letter', 'communication', 'send this'
        ]) and len(conversation_history) > 5:
            actions.append({
                "type": "draft_email",
                "label": "Generate Email Template"
            })

        # Check if ready to create claim
        if any(keyword in response_lower for keyword in [
            'ready to file', 'file your claim', 'submit', 'proceed with filing'
        ]):
            actions.append({
                "type": "create_claim",
                "label": "File Dispute Claim"
            })

        return actions

    def summarize_conversation(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Summarize conversation and extract claim details.

        Args:
            messages: List of conversation messages

        Returns:
            Dictionary with extracted claim information
        """
        try:
            # Create summarization prompt
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
