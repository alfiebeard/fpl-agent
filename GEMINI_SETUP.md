# 🚀 Quick Setup Guide - Google Gemini API

## Why Gemini?

**Google Gemini has the BEST free tier for this FPL optimizer:**

| Feature | Gemini 1.5 Flash | OpenAI GPT-3.5 | Anthropic Claude |
|---------|------------------|-----------------|------------------|
| **Free Requests** | 15/minute | Limited credits | Very limited |
| **Daily Limit** | 1M tokens/day | ~$5 worth | Minimal |
| **Speed** | Very fast | Fast | Medium |
| **Quality** | Excellent | Good | Excellent |
| **Cost** | **FREE** | Paid after credits | Mostly paid |

## 🔧 Setup Steps

### 1. Get Your Free Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy your API key

### 2. Configure the FPL Optimizer

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file and add your API key:**
   ```env
   # Replace with your actual API key
   GEMINI_API_KEY=AIzaSyC-your-actual-api-key-here
   ```

3. **The system is already configured to use Gemini by default!** ✅

### 3. Install Dependencies (if not done already)

```bash
pip3 install --break-system-packages -r fpl_optimizer/requirements.txt
```

### 4. Test the LLM Approach

```bash
# Create a team using Gemini-powered expert insights
PYTHONPATH=/workspace python3 -c "
import sys
sys.path.insert(0, '/workspace')

from fpl_optimizer.main import main
import sys

sys.argv = ['main.py', 'create-llm', '--budget', '100.0', '--gameweek', '15']
main()
"
```

## 🎯 Usage Examples

### Create Team with Expert Insights
```bash
python3 fpl_optimizer/main.py create-llm --budget 100.0 --gameweek 15
```

### Get Weekly Recommendations
```bash
python3 fpl_optimizer/main.py weekly-llm --gameweek 15 --free-transfers 1
```

### Compare Both Approaches
```bash
python3 fpl_optimizer/main.py compare --budget 100.0 --gameweek 15
```

## 🔧 Configuration Options

The system is pre-configured with optimal Gemini settings in `config.yaml`:

```yaml
llm:
  provider: "gemini"  # Using Gemini by default
  model: "gemini-1.5-flash"  # Fast model with generous free tier
  max_tokens: 4000
  temperature: 0.7
  
  gemini:
    safety_settings:
      harassment: "BLOCK_NONE"      # Allow sports discussion
      hate_speech: "BLOCK_NONE"     # Allow competitive analysis
      sexually_explicit: "BLOCK_NONE"
      dangerous_content: "BLOCK_NONE"
    generation_config:
      candidate_count: 1
      max_output_tokens: 4000
      temperature: 0.7
      top_p: 0.8
      top_k: 40
```

## 🆓 Free Tier Limits

**Gemini 1.5 Flash Free Tier:**
- ✅ **15 requests per minute**
- ✅ **1,000,000 tokens per day**
- ✅ **No expiration**
- ✅ **No credit card required**

This is perfect for FPL analysis - you can:
- Create multiple teams per day
- Get weekly recommendations
- Compare approaches
- Analyze wildcard timing

## ⚡ Expected Performance

With Gemini API, you'll get:

```
================================================================================
FPL TEAM CREATION COMPLETE - LLM-based Expert Insights
================================================================================

SELECTED TEAM
================================================================================
Name                     Team           Pos  Price  Form   Total Pts  Captain 
--------------------------------------------------------------------------------
Haaland                  Man City       FWD  £12.1  8.2    156        C       
Salah                    Liverpool      MID  £13.2  7.8    142        VC      
Gabriel                  Arsenal        DEF  £6.0   6.1    89                 
...

Team Cost: £99.8m
Expected Points: 67.3
Confidence: 0.85

REASONING
================================================================================
Team selection based on expert consensus from Fantasy Football Scout, Reddit 
r/FantasyPL, and FPL Analytics. Key factors: Haaland's home fixtures against 
weaker opposition, Salah's penalty duties and Liverpool's attacking form...

EXPERT INSIGHTS USED
================================================================================
Expert insights from 12 sources:
Fantasy Football Scout (4 insights):
  - Haaland essential for upcoming fixtures
  - Liverpool defense offers great value
Reddit r/FantasyPL (3 insights):
  - Community consensus on captain picks
  - Transfer window impact analysis
...
```

## 🔄 Switching Providers

If you want to try other providers later, just update your `.env`:

```env
# For OpenAI
# OPENAI_API_KEY=your_openai_key

# For Anthropic  
# ANTHROPIC_API_KEY=your_anthropic_key
```

And update `config.yaml`:
```yaml
llm:
  provider: "openai"  # or "anthropic"
```

## 🎉 You're Ready!

Your FPL optimizer now has:
- ✅ **Gemini AI integration** with the best free tier
- ✅ **Expert insights** from web scraping
- ✅ **Dual approaches** (statistical + AI)
- ✅ **Weekly recommendations** 
- ✅ **Captain selection**
- ✅ **Wildcard analysis**

Start optimizing your FPL team with AI-powered expert insights! 🏆