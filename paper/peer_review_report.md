# Peer Review Report - Manatrix Paper

**Journal:** Computers & Security (Elsevier)
**Paper:** Manatrix: A Bio-Inspired Multi-Expert AI Framework for Intelligent Password Guessing and Automated Penetration Testing
**Review Date:** June 4, 2026
**Recommendation:** Major Revisions Required

---

## Overall Assessment

This paper presents a novel bio-inspired multi-expert AI framework for penetration testing and password guessing. The work addresses important challenges in AI-driven security automation and proposes innovative architectural contributions. The experimental evaluation is comprehensive and demonstrates promising results. However, several methodological clarifications and additional analyses are required before publication.

---

## Detailed Comments

### 1. Originality and Novelty

**Strengths:**
- The Bio-MoE architecture combining membrane potential dynamics with emotional state modulation is genuinely novel
- Integration of 20 domain experts with bio-inspired coordination addresses real limitations in existing LLM security tools
- MAMBA+DE approach for password guessing is innovative

**Concerns:**
- The relationship between the proposed "emotional state" and standard reinforcement learning state representations could be clarified. Is this fundamentally different from maintaining an internal state vector in RL?

**Recommendation:** Add discussion comparing emotional state dimensions to standard RL state representations and explain the conceptual advantages of the bio-inspired framing.

### 2. Technical Soundness

**Strengths:**
- Mathematical formulation of Bio-MoE gating is clear
- Three-tier routing mechanism is well-described
- Experimental design includes appropriate ablation studies

**Concerns:**

**2.1 Hyperparameter Sensitivity:**
The paper reports default values (γ=0.9, η=0.3, δ, ζ) but does not analyze sensitivity. How robust are the results to hyperparameter variations?

**Recommendation:** Add a sensitivity analysis section showing how performance varies with different decay rates, update rates, and emotional state parameters.

**2.2 Expert Overlap:**
With 20 experts, there is potential overlap in capabilities. The paper does not analyze redundancy or collaboration patterns between experts.

**Recommendation:** Add an expert overlap analysis showing which experts are activated together frequently and whether redundancy exists.

**2.3 Password Dataset Details:**
The paper mentions "10,000 password test set from leaked database subset" without sufficient detail about the dataset composition.

**Recommendation:** Provide:
- Source database name
- Time period of data collection
- Password policy context (if known)
- Distribution statistics (length, character classes)

### 3. Methodology

**Strengths:**
- Ablation study design (A1-A4) properly isolates component contributions
- Multiple test environments provide robustness
- Statistical significance testing with effect sizes is appropriate

**Concerns:**

**3.1 Sample Size Justification:**
The paper uses 400 samples for ablation studies. Is this sufficient given the 4 experimental conditions and multiple metrics?

**Recommendation:** Provide power analysis justification for sample size.

**3.2 LLM Provider Details:**
The paper mentions DeepSeek LLM but does not specify:
- Model version used
- Temperature settings
- Prompt templates
- Token limits

**Recommendation:** Add a reproducibility section with complete LLM configuration details.

**3.3 Environment Standardization:**
The four test environments (DVWA, Metasploitable2, Windows Server, HackTheBox) have different difficulty levels and vulnerability types. How is "success" defined consistently?

**Recommendation:** Provide explicit success criteria for each environment type.

### 4. Experimental Results

**Strengths:**
- Clear presentation of quantitative results
- Appropriate statistical tests
- Multiple comparison baselines

**Concerns:**

**4.1 Password Guessing Baseline Fairness:**
The paper compares MAMBA+DE against methods (Markov, PCFG, PassGPT, LSTM) but does not clarify whether:
- All methods were trained on the same dataset
- PassGPT used pre-trained or trained from scratch
- Hyperparameters were optimized for each baseline

**Recommendation:** Provide details on baseline training procedures and hyperparameter settings for fair comparison.

**4.2 Convergence Analysis:**
Figure 1 shows convergence steps but not learning curves. Understanding the learning dynamics would strengthen the claims.

**Recommendation:** Add learning curve plots showing performance over training episodes.

**4.3 Error Analysis:**
The paper does not analyze failure cases. What types of assessments did B4 fail on in the 25% unsuccessful cases?

**Recommendation:** Add failure case analysis identifying common failure patterns.

### 5. Discussion

**Strengths:**
- Good discussion of Bio-MoE implications
- Appropriate acknowledgment of limitations
- Ethical considerations included

**Concerns:**

**5.1 Computational Cost:**
The paper does not discuss computational overhead of Bio-MoE compared to standard MoE. The membrane potential and emotional state updates add computation.

**Recommendation:** Add computational cost analysis comparing Bio-MoE to baseline in terms of FLOPS or wall-clock time per inference.

**5.2 Scalability:**
The framework uses 20 experts. How would performance scale with more experts? Is there a point of diminishing returns?

**Recommendation:** Add expert count ablation showing performance with 5, 10, 15, 20, 25 experts.

### 6. Writing Quality

**Strengths:**
- Well-structured paper
- Clear mathematical notation
- Good use of figures and tables

**Minor Issues:**
- Some references are plausible but need verification (Caldara et al. 2024, Hapi et al. 2023, Gupta et al. 2024)
- Add figure callouts in text (currently missing for Figures 2-7)

### 7. Ethical Considerations

**Strengths:**
- Dual-use concerns acknowledged
- Safeguards mentioned

**Concerns:**
- Password guessing capabilities could be misused
- More detailed discussion of responsible deployment needed

**Recommendation:** Expand ethical considerations section with:
- Specific use restrictions
- Recommended organizational policies
- Coordination with ethical hacking community

---

## Specific Recommendations by Section

### Abstract
- Add specific confidence intervals for key results

### Introduction
- Add more specific problem motivation with industry statistics

### Related Work
- Add more recent 2024-2025 references on LLM security tools
- Discuss GPT-4o/Claude 3.5 Sonnet security capabilities

### Methodology
- Add hyperparameter sensitivity analysis
- Add expert overlap analysis
- Provide complete LLM configuration details

### Experiments
- Add learning curves
- Add failure case analysis
- Clarify success criteria per environment

### Results
- Add confidence intervals to all tables
- Add computational cost analysis

### Discussion
- Add expert count scalability analysis
- Expand ethical considerations

### Conclusion
- Add specific future work timeline

---

## Summary of Required Revisions

### Major Revisions (Required)

1. **Add hyperparameter sensitivity analysis** for Bio-MoE parameters
2. **Add expert overlap/scalability analysis** showing redundancy patterns
3. **Provide complete reproducibility details** including LLM configurations, baseline training procedures, dataset statistics
4. **Add failure case analysis** for unsuccessful penetration tests
5. **Add computational cost comparison** between Bio-MoE and baseline

### Minor Revisions (Recommended)

1. Verify all reference details and add DOI links
2. Add figure callouts in text for Figures 2-7
3. Add confidence intervals to quantitative results
4. Expand ethical considerations section
5. Add learning curve visualizations

---

## Recommendation

**Decision:** Major Revisions Required

The paper presents valuable contributions to AI-driven security automation with novel architectural innovations. The experimental results are promising and well-presented. However, the identified methodological gaps—particularly regarding hyperparameter sensitivity, reproducibility details, and failure analysis—must be addressed before the work is suitable for publication.

Upon addressing the major revisions, the paper would make a strong contribution to the Computers & Security journal.

---

**Reviewer Confidence:** High
**Expertise Area:** AI Security, Multi-Agent Systems, Bio-Inspired Computing

*Review Completed: June 4, 2026*