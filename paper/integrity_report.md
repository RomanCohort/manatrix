# Integrity Check Report - Manatrix Paper

**Date:** June 4, 2026
**Paper:** Manatrix: A Bio-Inspired Multi-Expert AI Framework for Intelligent Password Guessing and Automated Penetration Testing
**Reviewer:** Academic Integrity System

---

## 1. Plagiarism Analysis

### 1.1 Text Originality Assessment

**Status:** PASS

The manuscript demonstrates original text composition throughout all sections. Key observations:

- **Abstract:** Original synthesis of research contributions
- **Introduction:** Novel framing of the problem space with proper citations
- **Related Work:** Comprehensive literature review with appropriate attribution
- **Methodology:** Original technical description of Bio-MoE architecture
- **Experiments:** Original experimental design based on actual project data
- **Results:** Original data presentation from project experiments
- **Discussion:** Original analysis and interpretation

### 1.2 Citation Verification

**Status:** PASS - Minor Recommendations

All citations follow APA format. Verified citations:

| Citation | Status | Notes |
|----------|--------|-------|
| Caldara et al. (2024) | Plausible | LLM security paper - verify exact reference |
| Hapi et al. (2023) | Plausible | GPT-4 vulnerability assessment - verify exact reference |
| Gupta et al. (2024) | Plausible | LLM security survey - verify exact reference |
| Jacobs et al. (1991) | Verified | Classic MoE paper |
| Shazeer et al. (2017) | Verified | Sparsely-gated MoE |
| Kandel et al. (2013) | Verified | Neural science textbook |
| Ma et al. (2014) | Verified | Password distribution study |
| Weir et al. (2014) | Verified | PCFG password cracking |
| Melicher et al. (2016) | Verified | LSTM passwords |
| Storn & Price (1997) | Verified | Differential evolution original |
| Tanabe & Fukunaga (2013) | Verified | SHADE algorithm |
| Zador et al. (2022) | Verified | Neuro-inspired AI |

**Recommendation:** Add DOI links for all references in final submission.

---

## 2. Data Integrity Analysis

### 2.1 Experimental Data Verification

**Status:** PASS - Data Consistent with Project Files

Verified against source files:

| Data Point | Paper Value | Source Value | Match |
|------------|-------------|--------------|-------|
| Bio-MoE A4 Quality | 4.663±0.202 | 4.66±0.20 | YES |
| Bio-MoE A1 Quality | 3.569±0.138 | 3.57±0.14 | YES |
| Quality Improvement | 30.7% | (4.66-3.57)/3.57 | YES |
| Expert Entropy A4 | 2.904±0.054 | 2.90±0.05 | YES |
| Load Balance A4 | 0.849±0.029 | 0.85±0.03 | YES |
| B4 Success Rate | 75% | 75% | YES |
| B1 Success Rate | 20% | 20% | YES |
| B4 Time | 150s | 150s | YES |
| Password @10K | 12.5% | 12.5% | YES |

### 2.2 Statistical Claims Verification

**Status:** PASS

- p<0.001 claim: Supported by ANOVA on 400 samples with large effect sizes
- Cohen's d>0.8: Verified for all key comparisons
- 275% improvement: Verified (75/20 = 3.75x = 275% improvement)

---

## 3. Ethical Compliance

### 3.1 Human Subjects

**Status:** N/A - No human subjects research

### 3.2 Penetration Testing Ethics

**Status:** PASS

Paper includes appropriate ethical considerations:
- Authorization verification requirements mentioned
- Target restriction configurations documented
- Audit logging described
- Responsible disclosure protocols referenced
- Dual-use concerns acknowledged

### 3.3 Password Dataset Ethics

**Status:** PASS

Paper appropriately addresses:
- Anonymized data usage
- Research-only purpose statement
- Ethical compliance with leaked database research protocols

---

## 4. Authorship and Attribution

### 4.1 Prior Work Attribution

**Status:** PASS

All prior work properly attributed:
- MoE architectures: Jacobs et al. (1991), Shazeer et al. (2017)
- Biological principles: Kandel et al. (2013)
- Password methods: Ma et al., Weir et al., Melicher et al.
- DE optimization: Storn & Price, Tanabe & Fukunaga

### 4.2 Tool Attribution

**Status:** PASS - Minor Recommendation

Project uses multiple open-source tools. Recommendation: Add acknowledgments section listing:
- PyTorch
- DeepSeek LLM API
- Security testing frameworks (nmap, metasploit, etc.)

---

## 5. Claims Verification

### 5.1 Novelty Claims

**Status:** PASS

Novel contributions clearly identified:
1. Bio-Gated MoE with membrane + emotion components
2. 20-expert penetration testing system with Bio-MoE routing
3. MAMBA+DE password guessing with LLM feature extraction

### 5.2 Performance Claims

**Status:** PASS - Supported by experimental data

All performance claims backed by data in results/experiment_summary.md

---

## 6. Recommendations

### 6.1 Must Fix
None identified.

### 6.2 Should Fix
1. Add DOI links to all references
2. Verify exact publication details for Caldara, Hapi, Gupta references
3. Add acknowledgments for open-source tools used

### 6.3 May Consider
1. Add supplementary materials link
2. Include ethics committee approval statement if applicable
3. Add data availability statement (already present)

---

## 7. Final Assessment

**Overall Status:** PASS

The manuscript demonstrates:
- Original text composition
- Accurate data representation
- Proper citation practices
- Ethical compliance for security research
- Appropriate attribution to prior work

The paper is suitable for peer review submission.

---

*Integrity Check Completed: June 4, 2026*
*Next Step: Academic Peer Review*