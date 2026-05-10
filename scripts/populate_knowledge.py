"""
Populate Knowledge Base with CVE and Security Data
Run: python scripts/populate_knowledge.py
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.vector_store import VectorStore, EmbeddingService, Document


# Sample CVE data for knowledge base
CVE_DATA = [
    {"id": "CVE-2021-44228", "content": "Apache Log4j2 JNDI features used in configuration, log messages, and user input. Remote code execution via crafted LDAP lookup. Affected versions: 2.0-2.14.1. CVSS: 10.0", "severity": "critical"},
    {"id": "CVE-2017-0144", "content": "SMBv1 vulnerability in Windows Vista/7/8/10/Server. Remote code execution via malicious packets. EternalBlue exploit. CVSS: 9.3", "severity": "critical"},
    {"id": "CVE-2019-0708", "content": "Remote Desktop Services vulnerability. Pre-authentication RCE without user interaction. BlueKeep. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2020-1472", "content": "ZeroLogon. Netlogon protocol vulnerability allowing domain admin privilege. CVSS: 10.0", "severity": "critical"},
    {"id": "CVE-2021-34527", "content": "Print Spooler vulnerability allowing RCE and privilege escalation. PrintNightmare. CVSS: 8.8", "severity": "high"},
    {"id": "CVE-2017-5638", "content": "Apache Struts 2 content-type OGNL injection. RCE via crafted Content-Type header. CVSS: 10.0", "severity": "critical"},
    {"id": "CVE-2018-7600", "content": "Drupalgeddon2. Drupal core RCE via Form API. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2022-22954", "content": "Spring MVC RCE via Data binding. Spring4Shell. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2019-11510", "content": "Pulse Connect Secure SSL VPN arbitrary file read. CVSS: 10.0", "severity": "critical"},
    {"id": "CVE-2020-5902", "content": "F5 BIG-IP Traffic Management WebUI RCE. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2021-26855", "content": "Exchange Server SSRF allowing stolen emails. ProxyLogon. CVSS: 9.1", "severity": "critical"},
    {"id": "CVE-2021-27065", "content": "Exchange Server RCE via malicious RpcRemoteIsThisFunction. ProxyLogon. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2017-10271", "content": "Oracle WebLogic RCE via SOAP deserialization. CVSS: 9.8", "severity": "critical"},
    {"id": "CVE-2020-14871", "content": "Oracle WebLogic authentication bypass. CVSS: 7.5", "severity": "high"},
    {"id": "CVE-2022-41080", "content": "Exchange Server RCE via PowerShell. CVSS: 8.1", "severity": "high"},
]

# Attack techniques (MITRE ATT&CK inspired)
TECHNIQUES = [
    {"id": "T1566", "content": "Phishing: Spearphishing Attachment, Spearphishing Link, Spearphishing via Service", "category": "initial_access"},
    {"id": "T1190", "content": "Exploit Public-Facing Application: Web-based exploits", "category": "initial_access"},
    {"id": "T1133", "content": "External Remote Services: VPN, RDP, SSH from outside", "category": "initial_access"},
    {"id": "T1200", "content": "Exploit Public-Facing Application: Software vulnerabilities", "category": "initial_access"},
    {"id": "T1059", "content": "Command and Scripting Interpreter: PowerShell, CMD, Python, Bash", "category": "execution"},
    {"id": "T1047", "content": "Windows Management Instrumentation: WMIExec, Invoke-WMI", "category": "execution"},
    {"id": "T1028", "content": "Windows Remote Management: WinRM access", "category": "execution"},
    {"id": "T1053", "content": "Scheduled Task/Job: AT, Scheduled tasks", "category": "persistence"},
    {"id": "T1547", "content": "Boot or Logon Autostart Execution: Registry Run keys", "category": "persistence"},
    {"id": "T1053", "content": "Scheduled Task/Job: Cron, Task Scheduler", "category": "persistence"},
    {"id": "T1543", "content": "Create or Modify System Process: Services, dllhost", "category": "persistence"},
    {"id": "T1078", "content": "Valid Accounts: Default credentials, Stolen credentials", "category": "persistence"},
    {"id": "T1068", "content": "Exploitation for Privilege Escalation: Kernel exploits, DLL hijacking", "category": "privile_escalation"},
    {"id": "T1548", "content": "Abuse Elevation Control Mechanism: UAC bypass", "category": "privilege_escalation"},
    {"id": "T1134", "content": "Access Token Manipulation: Token stealing, UAC bypass", "category": "privilege_escalation"},
    {"id": "T1003", "content": "OS Credential Dumping: LSASS, SAM database", "category": "credential_access"},
    {"id": "T1555", "content": "Credentials from Password Stores: Browser, Keychain", "category": "credential_access"},
    {"id": "T1110", "content": "Brute Force: Password spraying, Credential stuffing", "category": "credential_access"},
    {"id": "T1552", "content": "Unsecured Credentials: Cached credentials, Configuration files", "category": "credential_access"},
    {"id": "T1083", "content": "File and Directory Discovery: Enumeration of sensitive files", "category": "discovery"},
    {"id": "T1082", "content": "System Information Discovery: Hostname, OS version", "category": "discovery"},
    {"id": "T1046", "content": "Network Service Discovery: Port scanning, Service enumeration", "category": "discovery"},
    {"id": "T1135", "content": "Network Share Discovery: Enum shares, DFS", "category": "discovery"},
    {"id": "T1021", "content": "Remote Services: RDP, SMB, SSH, WinRM", "category": "lateral_movement"},
    {"id": "T1080", "content": "Taint Shared Content: Spread via removable media", "category": "lateral_movement"},
    {"id": "T1550", "content": "Use Alternate Authentication Material: Pass the Hash, Golden ticket", "category": "lateral_movement"},
    {"id": "T1486", "content": "Data Encrypted for Impact: Ransomware encryption", "category": "impact"},
    {"id": "T1489", "content": "Service Stop: Stop services, Disable security tools", "category": "impact"},
    {"id": "T1529", "content": "System Shutdown/Reboot: Shutdown systems", "category": "impact"},
]

# Tool documentation
TOOLS = [
    {"id": "nmap", "content": "Network exploration and security scanning. Port scanning, service detection, OS detection. Common: nmap -sV -sC -oA scan <target>", "category": "scanning"},
    {"id": "metasploit", "content": "Penetration testing framework. Exploit development, payload generation, post-exploitation. msfconsole, msfvenom", "category": "exploitation"},
    {"id": "sqlmap", "content": "SQL injection detection and exploitation. Database enumeration, data extraction. sqlmap -u <url> --batch", "category": "exploitation"},
    {"id": "hydra", "content": "Password cracking tool. Brute force, password spraying. hydra -L users.txt -P passwords.txt <target> <service>", "category": "credential"},
    {"id": "hashcat", "content": "Fast password recovery. GPU acceleration, multiple hash types. hashcat -m 0 hash.txt wordlist.txt", "category": "credential"},
    {"id": "john", "content": "Password cracker. Single mode, wordlist mode. john --wordlist=wordlist.txt hash.txt", "category": "credential"},
    {"id": "responder", "content": "LLMNR/NBT-NS/mDNS poisoner. SMB relay, HTTP auth capture.", "category": "credential"},
    {"id": "mimikatz", "content": "Windows credential extractor. LSASS, Kerberos tickets, Pass-the-Hash. sekurlsa::logonpasswords", "category": "credential"},
    {"id": "crackmapexec", "content": "Post-exploitation toolkit. SMB enumeration, Pass-the-Hash, Kerberoasting. crackmapexec smb <target>", "category": "credential"},
    {"id": "bloodhound", "content": "Active Directory graph analysis. Paths, privilege escalation. neo4j console, bloodhound", "category": "ad"},
    {"id": "kerberoast", "content": "Kerberos TGS cracking. Kerberoasting, AS-REP roasting. getTGT.py, hashcat", "category": "ad"},
    {"id": "smbclient", "content": "SMB client. Share enumeration, file transfer. smbclient //<target>/<share>", "category": " Lateral_movement"},
    {"id": "psexec", "content": "Remote execution. Service creation, interactive session. psexec.py, Impacket", "category": "lateral_movement"},
    {"id": "evil-winrm", "content": "Windows Remote Management. Remote shell, password spraying. evil-winrm.py", "category": "lateral_movement"},
    {"id": "nikto", "content": "Web vulnerability scanner. CVE detection, misconfiguration. nikto -h <url>", "category": "web"},
    {"id": "gobuster", "content": "Directory/file enumeration. Web path discovery. gobuster dir -u <url>", "category": "web"},
    {"id": "dirb", "content": "Web content scanner. Directory discovery. dirb <url>", "category": "web"},
    {"id": "wpscan", "content": "WordPress security scanner. Plugin vulnerabilities. wpscan --url <url>", "category": "web"},
    {"id": "nuclei", "content": "Fast vulnerability scanner. Template-based. nuclei -u <target>", "category": "vulnerability"},
    {"id": "searchsploit", "content": "Exploit-DB search. Offline exploit search. searchsploit <term>", "category": "exploitation"},
]

# AWS vulnerabilities
AWS_ISSUES = [
    {"id": "AWS-S3-Public", "content": "S3 bucket public access. Misconfigured ACL allows public read/write. Detection: aws s3api get-bucket-acl --bucket <name>", "category": "cloud"},
    {"id": "AWS-IAM-Overprivileged", "content": "Overprivileged IAM role. Too many permissions. Detection: iam-simulator", "category": "cloud"},
    {"id": "AWS-Secret-Leaked", "content": "AWS credentials in code. Git history, config files. Detection: git secrets", "category": "cloud"},
    {"id": "AWS-S3-Bucket-Sniffing", "content": "S3 bucket enumeration. Predictable bucket names. Detection: dns enumeration", "category": "cloud"},
    {"id": "AWS-Lambda-Backdoor", "content": "Lambda function backdoor. Malicious function code. Detection: lambda.get_function", "category": "cloud"},
]


async def populate_knowledge():
    """Populate knowledge base with CVE and security data"""
    print("=" * 60)
    print("Populating Knowledge Base")
    print("=" * 60)

    embedding_service = EmbeddingService()
    vector_store = VectorStore(persist_dir="data/vector_store")

    total_added = 0

    # Add CVE data
    print(f"\n[1/5] Adding CVE data ({len(CVE_DATA)} entries)...")
    cve_docs = []
    for cve in CVE_DATA:
        doc = Document(
            id=cve["id"],
            content=cve["content"],
            doc_type="cve",
            metadata={"severity": cve["severity"]}
        )
        cve_docs.append(doc)

    # Add all CVEs at once
    try:
        embeddings = embedding_service.embed([d.content for d in cve_docs])
        vector_store.add_documents(cve_docs, embeddings)
        total_added = len(cve_docs)
        print(f"  Added {total_added} CVEs")
    except Exception as e:
        print(f"  Error: {e}")
        # Try adding one by one
        for doc in cve_docs:
            try:
                vector_store.add_documents([doc], embedding_service.embed([doc.content]))
                total_added += 1
            except:
                pass
        print(f"  Added {total_added} CVEs (fallback)")

    # Add techniques
    print(f"\n[2/5] Adding attack techniques ({len(TECHNIQUES)} entries)...")
    tech_docs = [Document(id=t["id"], content=t["content"], doc_type="technique", metadata={"category": t["category"]}) for t in TECHNIQUES]
    try:
        embeddings = embedding_service.embed([d.content for d in tech_docs])
        vector_store.add_documents(tech_docs, embeddings)
        techniques_added = len(tech_docs)
    except:
        techniques_added = 0
    print(f"  Added {techniques_added} techniques")

    # Add tools
    print(f"\n[3/5] Adding tool documentation ({len(TOOLS)} entries)...")
    tool_docs = [Document(id=t["id"], content=t["content"], doc_type="tool", metadata={"category": t["category"]}) for t in TOOLS]
    try:
        embeddings = embedding_service.embed([d.content for d in tool_docs])
        vector_store.add_documents(tool_docs, embeddings)
        tools_added = len(tool_docs)
    except:
        tools_added = 0
    print(f"  Added {tools_added} tools")

    # Add AWS issues
    print(f"\n[4/5] Adding AWS security issues ({len(AWS_ISSUES)} entries)...")
    aws_docs = [Document(id=i["id"], content=i["content"], doc_type="cloud", metadata={"category": i["category"]}) for i in AWS_ISSUES]
    try:
        embeddings = embedding_service.embed([d.content for d in aws_docs])
        vector_store.add_documents(aws_docs, embeddings)
        aws_added = len(aws_docs)
    except:
        aws_added = 0
    print(f"  Added {aws_added} AWS issues")

    # Final count
    try:
        final_count = vector_store.count()
    except:
        final_count = total_added + techniques_added + tools_added + aws_added

    print(f"\n[5/5] Knowledge base population complete!")
    print(f"  Total documents: {final_count}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"CVE entries:          {total_added}")
    print(f"Attack techniques:   {techniques_added}")
    print(f"Tool documentation: {tools_added}")
    print(f"Cloud issues:      {aws_added}")
    print(f"-------------------")
    print(f"Total:             {total_added + techniques_added + tools_added + aws_added}")
    print("=" * 60)

    # Save stats
    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_documents": final_count,
        "cve_entries": total_added,
        "technique_entries": techniques_added,
        "tool_entries": tools_added,
        "cloud_entries": aws_added
    }

    with open("data/knowledge_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    return stats


if __name__ == "__main__":
    asyncio.run(populate_knowledge())