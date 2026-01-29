"""
Tests for Policy Engine
"""

import pytest
from datetime import datetime, timedelta
from src.governance.policy_engine import PolicyEngine


class TestPolicyEngine:
    """Test cases for PolicyEngine"""
    
    @pytest.fixture
    def policy_engine(self):
        """Create a PolicyEngine instance for testing"""
        return PolicyEngine()
    
    def test_load_policies(self, policy_engine):
        """Test that policies load correctly"""
        assert policy_engine.policy_config is not None
        assert policy_engine.mandatory_docs_config is not None
        assert policy_engine.last_loaded is not None
    
    def test_eligibility_check(self, policy_engine):
        """Test eligibility checking"""
        # Valid case
        is_eligible, errors = policy_engine.check_eligibility(
            dispute_amount=10000.0,
            invoice_date=datetime.now() - timedelta(days=30),
            has_msme_registration=True,
            registration_type="Udyam Registration"
        )
        assert is_eligible
        assert len(errors) == 0
        
        # Invalid case - no registration
        is_eligible, errors = policy_engine.check_eligibility(
            dispute_amount=10000.0,
            invoice_date=datetime.now() - timedelta(days=30),
            has_msme_registration=False
        )
        assert not is_eligible
        assert len(errors) > 0
    
    def test_get_mandatory_documents(self, policy_engine):
        """Test getting mandatory documents for dispute type"""
        docs = policy_engine.get_mandatory_documents("payment_delay")
        assert "invoice" in docs
        assert "msme_registration" in docs
        assert "delivery_proof" in docs
    
    def test_settlement_range(self, policy_engine):
        """Test settlement range calculation"""
        min_amount, max_amount = policy_engine.get_settlement_range(10000.0)
        assert min_amount <= max_amount
        assert min_amount >= 0
        assert max_amount <= 10000.0
    
    def test_interest_calculation(self, policy_engine):
        """Test interest calculation"""
        principal = 10000.0
        start_date = datetime.now() - timedelta(days=365)
        interest = policy_engine.calculate_interest(principal, start_date)
        assert interest > 0
        assert interest <= principal * 0.20  # Should be around 18% for 1 year

