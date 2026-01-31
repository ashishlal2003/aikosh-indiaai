"""
Conversation service for handling AI chat interactions.
Integrates Groq LLM for conversational dispute resolution assistance.
"""

from dotenv import load_dotenv
import os
from groq import Groq
from typing import List, Dict, Optional

load_dotenv()


class ConversationService:
    """Service for managing AI conversations about MSME disputes."""

    SYSTEM_PROMPT = """You are an expert MSME (Micro, Small, and Medium Enterprises) dispute resolution assistant in India. Your role is to help business owners file payment disputes under the MSMED Act, 2006.

Your responsibilities:
1. Gather information about unpaid invoices and payment disputes
2. Ask clarifying questions to understand the situation
3. Request necessary documents (invoices, purchase orders, delivery receipts, contracts)
4. Explain MSMED Act provisions (especially Section 15 - interest on delayed payments)
5. Provide negotiation strategies
6. Draft professional communication to buyers
7. Guide through the dispute resolution process

Key information you need to collect:
- Buyer/Customer details (name, address, GSTIN)
- Amount owed
- Invoice details (number, date, amount)
- Payment terms agreed upon
- Days overdue
- Supporting documents (PO, invoice, delivery proof, contract)

MSMED Act Key Points:
- Section 15: Buyers must pay within 45 days of acceptance or deemed acceptance
- Interest: 3x bank rate on delayed payments
- Dispute resolution through MSME Facilitation Council
- No court fees for MSMEs

Communication Style:
- Be empathetic and supportive
- Use simple language (avoid legal jargon unless explaining)
- Be conversational and friendly
- Ask one or two questions at a time (don't overwhelm)
- Provide actionable advice
- Support English, Hindi, and other Indian languages if user switches

Important: Always be helpful, never make definitive legal claims, suggest consulting a lawyer for complex cases."""

    def __init__(self):
        """Initialize conversation service with Groq client."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=self.groq_api_key)
        self.model = "llama-3.1-8b-instant"  # Using Llama 3 70B for best conversational quality

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
            # Prepare messages with system prompt
            chat_messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT}
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
