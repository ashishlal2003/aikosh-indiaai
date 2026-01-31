# AI Kosh Datasets Integration

## Datasets Downloaded & Used

### 1. KathBath Hindi Validation Dataset
- **Source:** AI Kosh Portal - IndicVoices Collection
- **Type:** Audio (Hindi speech samples)
- **Files:** 4 WAV files in `kathbath_hindi_validation/`
- **Use Case:**
  - Testing Groq Whisper-large-v3 transcription accuracy
  - Validating Hindi language detection
  - Ensuring voice input works for non-English MSMEs
- **Implementation:** Day 2 - Voice Input Testing

### 2. Karnataka MSME Registration List
- **Source:** AI Kosh Portal - MSME Datasets
- **Type:** JSON (MSME registration data)
- **File:** `msme_karnataka_list.json`
- **Contains:** Unit names, addresses, enterprise types, NIC codes, registration details
- **Use Case:**
  - Creating realistic demo claims with actual MSME names
  - MSME ID format validation patterns
  - UI statistics ("Powered by 50,000+ Karnataka MSMEs from AI Kosh")
- **Implementation:** Day 10 - AI Kosh Showcase, Day 14 - Demo Data

## Datasets Still Needed

### High Priority
- Tamil/Telugu voice samples (for broader language coverage)
- MSMED Act 2006 legal text (for RAG knowledge base)

### Medium Priority
- Sample Indian invoice images (for OCR testing)
- ODR dispute case studies (for negotiation patterns)

### Low Priority
- More regional language samples (Kannada, Bengali, Marathi)

## Documentation for Judges

This integration demonstrates our commitment to leveraging government AI resources:
- **4 Hindi voice samples** validate multilingual voice input
- **Karnataka MSME data** ensures realistic demo scenarios
- **Transparent usage** - we document what we found vs. what we hoped for

Even with limited datasets available, we've maximized their usage to build an accessible, India-first MSME ODR solution.
