"""
Rule-based knowledge base for the proposal-generation engine.

This is deliberately NOT a call to an LLM. It is a keyword / pattern matching
layer over a small library of domain templates (standards, work packages,
effort-by-discipline hour tables, and "what's missing" checks) modelled on
the E2E Harness project's own AI-Assisted Proposal Generation concept:
  Internal Knowledge Layer -> Project Understanding Layer -> Proposal Generation Layer

Swap DOMAINS/keyword matching for a real LLM call later without changing the
app around it -- engine.py is the seam where that swap happens.
"""

DISCIPLINES = ["ELE", "ELN", "SW", "MEC", "MFG", "SYS", "T&V", "QA", "PM"]
DISCIPLINE_FULL = [
    "Electrical engineering", "Electronics / hardware", "Software",
    "Mechanical engineering", "Manufacturing engineering", "Systems engineering",
    "Test and validation", "Quality / homologation", "Programme management",
]

# Each domain: id, label, keyword triggers (weighted), standards, work packages,
# base contingency %, generic risks, and missing-info checks.
DOMAINS = {
    "harness_lv": {
        "label": "Low-voltage chassis / body harness",
        "keywords": {
            "harness": 2, "wiring": 2, "loom": 2, "chassis": 1, "body": 1,
            "connector": 1, "terminal": 1, "crimp": 1, "wire": 1, "cable": 1,
            "build-to-print": 3, "build to print": 3, "bom": 1,
        },
        "standards": [
            ["ISO 19642 / ISO 6722", "Road-vehicle cable specification"],
            ["ISO 8092 series", "Connections for on-board electrical wiring harnesses"],
            ["USCAR-21", "Terminal-to-wire crimp performance validation"],
            ["IPC/WHMA-A-620 Class 2", "Acceptance criteria for cable and harness assemblies"],
            ["IATF 16949 / AIAG PPAP / APQP", "Automotive quality system and production part approval"],
        ],
        "work_packages": [
            ["WP1", "Drawing / requirement review (DFM)", "Review inputs, raise engineering queries, flag obsolete or single-source parts.", [24, 0, 0, 0, 60, 0, 0, 16, 8]],
            ["WP2", "Manufacturing process design", "Process flow, cut-and-crimp routing, work instructions, line balancing.", [0, 0, 0, 16, 180, 0, 0, 24, 16]],
            ["WP3", "Tooling and crimp validation", "Applicator/die selection, crimp height and pull-force validation.", [0, 0, 0, 0, 120, 0, 80, 40, 8]],
            ["WP4", "Test equipment and fixtures", "Continuity / hi-pot fixtures, connector-presence checks.", [40, 16, 20, 24, 60, 0, 60, 8, 8]],
            ["WP5", "PPAP and launch support", "Control plan, PFMEA, PSW submission, ramp support.", [0, 0, 0, 0, 60, 0, 40, 120, 40]],
        ],
        "contingency": 8,
        "missing_checks": [
            ("volume", r"\b\d[\d,]*\s*(units?|vehicles?|pcs?|pieces?)\s*(per\s*year|/\s*yr|p\.?a\.?)\b", "What is the target annual volume per variant?"),
            ("connector_source", r"custom(er)?[- ]?(nominated|approved|supplied)|approved (vendor|supplier) list", "Are connectors/terminals customer-nominated, or open to supplier sourcing?"),
            ("design_authority", r"design (authority|responsibility|owner)", "Who holds design authority — customer or supplier?"),
        ],
        "risks": [
            ["Drawing/requirement errors found late", "Rework, PPAP delay", "Formal DFM gate before tooling order; queries logged and closed"],
            ["Long lead time for connectors/terminals", "Ramp delayed", "Early buy forecast; buffer stock on critical items"],
        ],
    },
    "harness_hv": {
        "label": "High-voltage harness / EV powertrain",
        "keywords": {
            "high voltage": 3, "hv ": 2, " hv": 2, "hvil": 3, "battery": 1, "inverter": 1,
            "600v": 2, "800v": 2, "400v": 2, "pdu": 2, "shield": 1, "orange": 1,
            "dc fast charge": 2, "charging": 1, "electric vehicle": 2, "ev ": 1,
        },
        "standards": [
            ["ISO 6469-3", "Electrical safety of EVs: protection against electric shock"],
            ["UN ECE R100", "Electric power train safety (approval)"],
            ["ISO 19642-4 / LV 216", "HV cable specification and testing"],
            ["IEC 60664-1", "Creepage and clearance at interfaces"],
            ["ISO 26262", "HVIL and interlock functional safety"],
            ["CISPR 25 / ISO 11452", "EMC (shield termination performance)"],
        ],
        "work_packages": [
            ["WP1", "HV requirements and safety concept", "Voltage/current/insulation targets, HVIL concept, touch-safe strategy.", [60, 20, 0, 0, 0, 80, 0, 24, 12]],
            ["WP2", "HV architecture and cable sizing", "Current profile, thermal derating, shield concept, connector selection.", [140, 0, 0, 20, 0, 60, 0, 8, 8]],
            ["WP3", "Schematic and interlock design", "HV schematic, HVIL circuit, isolation-monitoring interface.", [120, 40, 20, 0, 0, 20, 0, 8, 8]],
            ["WP4", "3D routing and harness design", "Routing with clearances, shielded-cable bend radii, drawings, BOM.", [60, 0, 0, 260, 40, 0, 0, 16, 16]],
            ["WP5", "Prototype build and validation", "Dielectric withstand, insulation resistance, thermal cycle, vibration, DVP&R.", [40, 0, 0, 20, 100, 20, 320, 40, 16]],
            ["WP6", "HV manufacturing industrialisation", "HV-qualified cell, operator HV training, hi-pot test stations, traceability.", [0, 0, 0, 16, 260, 0, 60, 120, 24]],
        ],
        "contingency": 14,
        "missing_checks": [
            ("voltage", r"\b\d{2,3}\s*v\b", "What is the nominal / maximum system voltage?"),
            ("current", r"\b\d{1,4}\s*a\b", "What is the continuous / peak current rating?"),
            ("charging_std", r"ccs|mcs|gb/?t|chademo", "Which fast-charge standard (if any) must the harness support?"),
        ],
        "risks": [
            ["Shield termination failures under vibration", "EMC non-compliance, field faults", "Early termination trials; vibration test at prototype"],
            ["HV-trained workforce availability", "Ramp delayed", "Training programme starts early; certified operator matrix"],
        ],
    },
    "dcdc_pdu": {
        "label": "DC-DC converter / smart power distribution unit",
        "keywords": {
            "dc-dc": 3, "dc/dc": 3, "converter": 2, "pdu": 2, "power distribution": 2,
            "current sensing": 2, "voltage monitoring": 2, "fault isolation": 2,
            "smart pcb": 3, "pcb": 1, "contactor": 1, "precharge": 1, "shunt": 1,
        },
        "standards": [
            ["ISO 26262", "Functional safety of the converter / PDU"],
            ["ISO 6469-3 / UN ECE R100", "HV safety and isolation"],
            ["IEC 61557-8", "Insulation monitoring devices"],
            ["ISO 21434 / UN R155", "Cybersecurity engineering for the connected ECU"],
            ["IEC 60664-1 / IPC-2221 / IPC-6012 Class 3", "Creepage, clearance and PCB rules for HV"],
            ["AEC-Q100 / Q101 / Q200", "Component qualification"],
        ],
        "work_packages": [
            ["WP1", "Requirements and safety concept", "HARA, safety goals, fault-reaction time budget, diagnostic coverage targets.", [40, 60, 20, 0, 0, 240, 0, 40, 16]],
            ["WP2", "Power-path / topology design", "Busbar/contactor layout or topology trade study, thermal design.", [140, 200, 0, 100, 0, 40, 0, 8, 8]],
            ["WP3", "PCB hardware design", "Isolated sensing, redundant measurement, safety MCU, power supply.", [0, 400, 40, 0, 0, 60, 0, 16, 12]],
            ["WP4", "Firmware and diagnostics", "Safety-rated firmware, fault-isolation logic, CAN-FD, UDS, bootloader.", [0, 40, 460, 0, 0, 60, 40, 24, 12]],
            ["WP5", "Prototype builds (A/B samples)", "Prototype build and assembly process development.", [20, 60, 0, 40, 200, 0, 40, 40, 16]],
            ["WP6", "Validation and verification", "Isolation, dielectric, EMC, fault-injection and reaction-time measurement.", [40, 80, 60, 20, 0, 40, 440, 40, 20]],
        ],
        "contingency": 15,
        "missing_checks": [
            ("power_rating", r"\bk?w\b|\bkw\b|\d+\s*(amp|a)\b", "What is the rated power / continuous current?"),
            ("asil", r"asil", "What ASIL / safety-integrity level applies to the monitoring and isolation functions?"),
            ("comms", r"can-?fd|can\b|lin\b|ethernet", "What vehicle communication bus must the smart PCB use?"),
        ],
        "risks": [
            ["Sensing accuracy drift with temperature", "Measurement error", "Temperature compensation; calibration at end-of-line"],
            ["Fault-reaction time exceeds budget", "Safety non-compliance", "Hardware-based trip path; timing measured at first sample"],
        ],
    },
    "architecture_schematic": {
        "label": "Electrical architecture / schematic design",
        "keywords": {
            "architecture": 3, "schematic": 3, "zonal": 2, "domain controller": 2,
            "network topology": 2, "can bus": 1, "gateway": 1, "system owner": 1,
            "electrical system": 1, "e/e architecture": 3, "power distribution": 1,
        },
        "standards": [
            ["ISO 26262", "Functional safety at system level"],
            ["ISO 21434 / UN R155 / UN R156", "Cybersecurity and software update management"],
            ["ISO 11898-1/-2, ISO 17987 (LIN)", "In-vehicle networks"],
            ["ISO 14229 (UDS) / ISO 13400 (DoIP)", "Diagnostics"],
            ["ISO 16750 series", "Environmental and electrical loads"],
        ],
        "work_packages": [
            ["WP1", "Requirements and feature catalogue", "System-owner input per function including location, variant matrix.", [80, 20, 20, 0, 0, 240, 0, 24, 20]],
            ["WP2", "Electrical architecture concept", "Topology trade study, power distribution, grounding, network topology.", [200, 60, 40, 0, 0, 240, 0, 16, 12]],
            ["WP3", "Signal, network and load database", "Signal list, message matrix, load and current budgets.", [160, 20, 120, 0, 0, 120, 0, 12, 8]],
            ["WP4", "Schematic design", "System schematics and wiring diagrams, protection and ground schemes.", [400, 0, 0, 0, 0, 40, 0, 32, 16]],
            ["WP5", "Simulation and verification", "Power/voltage-drop simulation, network timing simulation, DRC.", [100, 20, 80, 0, 0, 120, 160, 16, 8]],
        ],
        "contingency": 10,
        "missing_checks": [
            ("topology_pref", r"zonal|domain", "Is there a preference between zonal and domain topology, or is it open?"),
            ("ecu_supplier", r"ecu supplier|controller supplier", "Which ECU/controller suppliers are already nominated?"),
            ("weight_cost_target", r"weight target|cost target|kg\b", "Are there weight or cost targets the architecture must meet?"),
        ],
        "risks": [
            ["Late feature changes re-partition zones", "Cost and schedule impact", "Feature freeze at concept gate; change board with impact assessment"],
            ["ECU interface data arrives late", "Pin allocation blocked", "Assumption-based allocation with tracked open items"],
        ],
    },
    "defence": {
        "label": "Defence / MIL-spec",
        "keywords": {
            "mil-std": 3, "mil-dtl": 3, "def stan": 3, "military": 2, "armoured": 2,
            "nbc": 1, "blast": 1, "1553": 2, "itar": 2, "export control": 2,
        },
        "standards": [
            ["MIL-STD-1275E / DEF STAN 61-5", "28 V vehicle power characteristics"],
            ["MIL-STD-461G / DEF STAN 59-411", "EMC and EMI requirements"],
            ["MIL-STD-810H", "Environmental engineering considerations and tests"],
            ["MIL-DTL-38999 / MIL-DTL-26482 / MIL-DTL-5015", "Circular connector families"],
            ["MIL-DTL-27500 / SAE AS22759", "Cable and wire specifications"],
            ["ITAR / UK Export Control", "Export and handling controls"],
        ],
        "work_packages": [
            ["WP1", "Requirements and compliance matrix", "Map customer specification and referenced standards; ICDs.", [80, 0, 0, 20, 0, 120, 0, 40, 16]],
            ["WP2", "Electrical design and schematics", "Power distribution, circuit protection, grounding/bonding, EMC design rules.", [320, 40, 0, 0, 0, 40, 0, 24, 16]],
            ["WP3", "Harness design and routing", "3D routing, shielding/backshell design, drawings, BOM.", [80, 0, 0, 380, 60, 0, 0, 24, 20]],
            ["WP4", "Qualification planning and testing", "Shock, vibration, salt fog, EMC test plans and execution.", [40, 0, 0, 20, 0, 60, 360, 60, 16]],
            ["WP5", "Manufacturing and configuration control", "Special process approvals, tooling, traceability, configuration management.", [0, 0, 0, 0, 200, 0, 20, 140, 40]],
        ],
        "contingency": 15,
        "missing_checks": [
            ("classification", r"classified|classification level|security clearance", "What classification level applies to the design data?"),
            ("standard_edition", r"rev(ision)?\s*[a-z0-9]|edition", "Which edition/revision of each referenced standard is contractual?"),
            ("export_control", r"itar|export control|end[- ]user", "Are there export-control or end-user restrictions on this programme?"),
        ],
        "risks": [
            ["Specification conflicts between MIL and national standards", "Rework and dispute", "Compliance matrix with waiver route agreed at PDR"],
            ["Restricted/obsolete connector supply", "Delay", "Early identification of long-lead and controlled items"],
        ],
    },
    "other": {
        "label": "General electrical / harness engineering (no strong domain match)",
        "keywords": {},
        "standards": [
            ["ISO 9001 / IATF 16949", "Quality management system (confirm which applies)"],
            ["Customer-specific standards", "To be confirmed once the customer specification is available"],
        ],
        "work_packages": [
            ["WP1", "Requirements clarification", "Structure the customer input into a working requirements set; log open questions.", [40, 0, 0, 0, 0, 80, 0, 16, 12]],
            ["WP2", "Concept design", "First-pass technical concept sufficient to scope the remaining work packages.", [80, 20, 0, 40, 0, 40, 0, 8, 8]],
            ["WP3", "Detailed design and documentation", "Detailed design deliverables appropriate to the confirmed scope.", [160, 0, 0, 80, 20, 0, 0, 16, 16]],
        ],
        "contingency": 15,
        "missing_checks": [
            ("project_type", r"harness|schematic|architecture|dc-?dc|pdu|converter", "What kind of electrical deliverable is this — harness, schematic, architecture, or something else?"),
            ("scope_type", r"build.to.print|design.and.manufactur|design only|manufactur(e|ing) only", "Is this build-to-print, design-only, or design-and-manufacture?"),
        ],
        "risks": [
            ["Insufficient input to scope the work reliably", "Inaccurate estimate", "Treat this draft as provisional; confirm scope before quoting"],
        ],
    },
}

# Cross-domain signal keywords that add an extra work package regardless of matched domain
ADDON_SIGNALS = {
    "functional_safety": {
        "keywords": {"asil": 3, "functional safety": 3, "safety-critical": 2, "safety critical": 2, "iso 26262": 3},
        "wp": ["WPX", "Functional safety concept (add-on)", "HARA, safety goals allocation, safety case contribution — triggered by safety-related language in the inputs.", [0, 20, 20, 0, 0, 160, 0, 60, 8]],
    },
    "regulatory_homologation": {
        "keywords": {"homologation": 3, "type approval": 3, "regulatory": 1, "aisin": 0, "un ece": 2, "ais-": 3, "whole vehicle type approval": 3},
        "wp": ["WPX", "Homologation / approval evidence (add-on)", "Test-house coordination and documentation for regulatory approval — triggered by approval-related language in the inputs.", [20, 0, 0, 0, 0, 40, 60, 120, 16]],
    },
    "low_volume_prototype": {
        "keywords": {"prototype only": 3, "low volume": 2, "demonstrator": 2, "one-off": 2, "proof of concept": 2},
        "wp": None,  # handled as a scaling rule, not an added WP
    },
    "high_volume": {
        "keywords": {"high volume": 2, "mass production": 2, "million units": 3},
        "wp": None,
    },
}
