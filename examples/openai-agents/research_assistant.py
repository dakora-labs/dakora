import os
import json
from datetime import datetime
from dotenv import load_dotenv
from agents import Agent
from dakora.vault import Vault

load_dotenv()

vault = Vault(config_path="dakora.yaml")


def create_research_planner():
    prompt = vault.get("planner_system")
    return Agent(
        name="Research Planner",
        instructions=prompt.render(),
        model="gpt-4o-mini"
    )


def create_analyst():
    prompt = vault.get("analyst_system")
    return Agent(
        name="Analyst",
        instructions=prompt.render(
            subtopic="placeholder",
            questions=["placeholder"]
        ),
        model="gpt-4o-mini"
    )


def create_synthesizer():
    prompt = vault.get("synthesizer_system")
    return Agent(
        name="Synthesizer",
        instructions=prompt.render(
            findings_text="placeholder"
        ),
        model="gpt-4o-mini"
    )


def create_coordinator(research_topic: str, output_format: str = "markdown", depth_level: str = "standard"):
    prompt = vault.get("coordinator_system")

    planner = create_research_planner()
    synthesizer = create_synthesizer()

    return Agent(
        name="Research Coordinator",
        instructions=prompt.render(
            research_topic=research_topic,
            output_format=output_format,
            depth_level=depth_level
        ),
        model="gpt-4o"
    )


def conduct_research(topic: str, num_subtopics: int = 3, focus_areas: list = None):
    print(f"\n🔬 Starting research on: {topic}\n")

    planner_prompt = vault.get("planner_system")
    planner_instructions = planner_prompt.render(
        topic=topic,
        num_subtopics=num_subtopics,
        focus_areas=focus_areas or []
    )

    planner = Agent(
        name="Research Planner",
        instructions=planner_instructions,
        model="gpt-4o-mini"
    )

    print("📋 Planning research strategy...")
    from agents import Runner
    plan_result = Runner.run_sync(planner, f"Create a research plan for: {topic}")

    try:
        plan_data = json.loads(plan_result.final_output)
    except json.JSONDecodeError:
        print("⚠️  Planner output wasn't valid JSON, using fallback")
        plan_data = {
            "subtopics": [
                {
                    "title": f"Aspect {i+1} of {topic}",
                    "questions": [f"What are the key aspects of {topic}?"],
                    "sources": ["general research"],
                    "priority": i+1
                }
                for i in range(num_subtopics)
            ],
            "research_strategy": "General research approach"
        }

    print(f"\n📊 Research Plan:")
    print(f"Strategy: {plan_data.get('research_strategy', 'N/A')}")
    print(f"Subtopics: {len(plan_data.get('subtopics', []))}\n")

    findings = []

    for idx, subtopic in enumerate(plan_data.get("subtopics", []), 1):
        print(f"🔍 Analyzing subtopic {idx}/{len(plan_data['subtopics'])}: {subtopic['title']}")

        analyst_prompt = vault.get("analyst_system")
        analyst_instructions = analyst_prompt.render(
            subtopic=subtopic["title"],
            questions=subtopic.get("questions", []),
            context=f"Part of broader research on: {topic}",
            analysis_depth="standard",
            source_types=subtopic.get("sources", [])
        )

        analyst = Agent(
            name=f"Analyst-{idx}",
            instructions=analyst_instructions,
            model="gpt-4o-mini"
        )

        analysis_result = Runner.run_sync(
            analyst,
            f"Analyze: {subtopic['title']}"
        )

        findings.append({
            "subtopic": subtopic["title"],
            "analysis": analysis_result.final_output
        })
        print(f"✓ Analysis complete\n")

    print("🔄 Synthesizing findings...")

    findings_text = "\n\n".join([
        f"### {f['subtopic']}\n\n{f['analysis']}"
        for f in findings
    ])

    synthesizer_prompt = vault.get("synthesizer_system")
    synthesizer_instructions = synthesizer_prompt.render(
        findings_text=findings_text,
        synthesis_style="balanced",
        audience_level="general"
    )

    synthesizer = Agent(
        name="Synthesizer",
        instructions=synthesizer_instructions,
        model="gpt-4o"
    )

    synthesis_result = Runner.run_sync(
        synthesizer,
        "Synthesize the research findings into a coherent report"
    )

    print("✓ Synthesis complete\n")

    final_report = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "plan": plan_data,
        "findings": findings,
        "synthesis": synthesis_result.final_output
    }

    return final_report


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python research_assistant.py <research_topic>")
        print("\nExample:")
        print('  python research_assistant.py "AI agent frameworks in 2025"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    result = conduct_research(
        topic=topic,
        num_subtopics=3,
        focus_areas=[]
    )

    print("=" * 80)
    print("\n📄 RESEARCH REPORT\n")
    print("=" * 80)
    print(result["synthesis"])
    print("\n" + "=" * 80)

    output_file = f"research_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Full report saved to: {output_file}")