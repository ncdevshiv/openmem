"""
Reflection Engine for OpenMem.
Self-correction and improvement system that evaluates interactions and updates behavior.
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from memory_store import get_vector_db
from memory_store.memory_manager import MemoryManager
from memory_store.user_model import UserModel


class ReflectionEngine:
    """
    Self-reflection and improvement engine.
    
    After each significant interaction, evaluates:
    - Did we help effectively?
    - What could be improved?
    - What should we remember?
    - Are there patterns we should adapt to?
    
    Components:
    1. Session Reflection - analyze a single session
    2. Pattern Reflection - look for cross-session patterns
    3. Self-Correction - update internal state based on reflections
    """
    
    def __init__(self):
        self.vector_db = get_vector_db()
        self.memory_manager = MemoryManager()
        self.user_model = UserModel()

        # Reflection state
        self.reflection_log = os.path.join(
            os.path.dirname(__file__), "..", "data", "reflections.json"
        )
        os.makedirs(os.path.dirname(os.path.abspath(self.reflection_log)), exist_ok=True)
        self.reflections = self._load_reflections()

        # Improvement actions queue
        self.improvements_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "improvements.json"
        )
        os.makedirs(os.path.dirname(os.path.abspath(self.improvements_file)), exist_ok=True)
        self.improvements = self._load_improvements()
    
    def _load_reflections(self) -> Dict:
        """Load reflection history."""
        if os.path.exists(self.reflection_log):
            with open(self.reflection_log, 'r') as f:
                return json.load(f)
        return {
            "session_reflections": [],  # List of per-session reflections
            "cross_session_reflections": [],  # Patterns noticed across sessions
            "corrections_made": [],  # Self-corrections applied
            "last_reflection": None
        }
    
    def _load_improvements(self) -> Dict:
        """Load pending improvements."""
        if os.path.exists(self.improvements_file):
            with open(self.improvements_file, 'r') as f:
                return json.load(f)
        return {
            "pending": [],      # Improvements to make
            "completed": [],    # Improvements that were made
            "rejected": []      # Improvements considered but rejected
        }
    
    def _save_reflections(self):
        """Save reflection history."""
        self.reflections["last_reflection"] = datetime.now().isoformat()
        with open(self.reflection_log, 'w') as f:
            json.dump(self.reflections, f, indent=2)
    
    def _save_improvements(self):
        """Save improvements queue."""
        with open(self.improvements_file, 'w') as f:
            json.dump(self.improvements, f, indent=2)
    
    def reflect_on_session(self, session_messages: List[Dict]) -> Dict:
        """
        Perform reflection on a single session.
        Uses LLM-based analysis when available, falls back to heuristic.

        Args:
            session_messages: List of message dicts with role, content, timestamp

        Returns:
            Reflection dict with analysis and recommended actions
        """
        reflection = {
            "session_id": session_messages[0].get("session_id", "unknown") if session_messages else "unknown",
            "timestamp": datetime.now().isoformat(),
            "turn_count": len(session_messages),
            "analysis": {},
            "outcome": None,
            "improvements_identified": [],
            "memories_to_create": [],
            "corrections_needed": []
        }

        if not session_messages:
            return reflection

        # Try LLM-based reflection first
        try:
            from core.llm import get_llm
            llm = get_llm()
            if llm.is_available:
                llm_result = llm.reflect(session_messages)
                return self._build_reflection_from_llm(reflection, session_messages, llm_result)
        except (ImportError, Exception):
            pass

        # Heuristic fallback (existing logic below)
        return self._reflect_heuristic(reflection, session_messages)

    def _build_reflection_from_llm(self, reflection: Dict, session_messages: List[Dict], llm_result: Dict) -> Dict:
        """Build reflection dict from LLM analysis."""
        user_msgs = [m for m in session_messages if m.get("role") == "user"]
        assistant_msgs = [m for m in session_messages if m.get("role") == "assistant"]

        reflection["analysis"]["user_message_count"] = len(user_msgs)
        reflection["analysis"]["assistant_message_count"] = len(assistant_msgs)

        # LLM outcome
        outcome = llm_result.get("outcome", "neutral")
        reflection["outcome"] = outcome
        reflection["analysis"]["sentiment"] = {
            "success": "positive",
            "failure": "frustrated",
        }.get(outcome, "neutral")

        # What went well
        for item in llm_result.get("what_went_well", []):
            reflection["improvements_identified"].append({
                "type": "reinforce",
                "description": item,
                "source": "llm_reflection",
            })

        # What to improve
        for item in llm_result.get("what_to_improve", []):
            reflection["improvements_identified"].append({
                "type": "fix_needed",
                "description": item,
                "source": "llm_reflection",
            })

        # Facts to remember
        for key, value in llm_result.get("facts_to_remember", {}).items():
            reflection["memories_to_create"].append({
                "type": "user_fact",
                "key": key,
                "value": value,
                "source": "llm_reflection",
            })

        # Knowledge gaps
        for gap in llm_result.get("knowledge_gaps", []):
            reflection["improvements_identified"].append({
                "type": "knowledge_gap",
                "description": f"Unknown topic: {gap}",
                "action": "Research and add to memory",
                "source": "llm_reflection",
            })

        # Apply reflection
        self.apply_reflection(reflection)
        return reflection

    def _reflect_heuristic(self, reflection: Dict, session_messages: List[Dict]) -> Dict:
        """Heuristic reflection (original logic, extracted to separate method)."""
        # Separate user and assistant messages
        user_msgs = [m for m in session_messages if m.get("role") == "user"]
        assistant_msgs = [m for m in session_messages if m.get("role") == "assistant"]

        reflection["analysis"]["user_message_count"] = len(user_msgs)
        reflection["analysis"]["assistant_message_count"] = len(assistant_msgs)

        # Analyze user's final message for outcome
        if user_msgs:
            final_user = user_msgs[-1].get("content", "").lower()

            # Success indicators
            if any(kw in final_user for kw in ["thanks", "perfect", "great", "awesome", "love it", "nice"]):
                reflection["outcome"] = "success"
                reflection["analysis"]["sentiment"] = "positive"
            elif any(kw in final_user for kw in ["still", "doesn't work", "not working", "wrong", "terrible"]):
                reflection["outcome"] = "failure"
                reflection["analysis"]["sentiment"] = "frustrated"
            elif any(kw in final_user for kw in ["okay", "ok", "alright"]):
                reflection["outcome"] = "neutral_accepted"
                reflection["analysis"]["sentiment"] = "neutral"
            else:
                reflection["outcome"] = "continues"
                reflection["analysis"]["sentiment"] = "neutral"

        # Identify what went well
        if reflection["outcome"] == "success":
            reflection["improvements_identified"].append({
                "type": "reinforce",
                "description": "This approach worked well - note the strategy used",
                "examples": [m.get("content", "")[:200] for m in assistant_msgs[-2:]]
            })

        # Identify what could be improved
        if reflection["outcome"] == "failure":
            reflection["improvements_identified"].append({
                "type": "fix_needed",
                "description": "User indicated the solution didn't work",
                "what_to_try": "different approach, more details, check prerequisites"
            })

            if user_msgs:
                self.user_model.behavior_patterns["frustration_indicators"].append({
                    "message_sample": user_msgs[-1].get("content", "")[:150],
                    "timestamp": datetime.now().isoformat()
                })

        # Check for knowledge gaps
        for msg in user_msgs:
            content = msg.get("content", "").lower()
            if any(kw in content for kw in ["what is", "how does", "tell me about"]):
                if len(content) < 100:
                    reflection["improvements_identified"].append({
                        "type": "knowledge_gap",
                        "description": f"User asked about: {content[:100]}",
                        "action": "Research and add to memory"
                    })

        # Extract facts
        for msg in user_msgs:
            content = msg.get("content", "")
            facts = self._extract_facts(content)
            for key, value in facts.items():
                reflection["memories_to_create"].append({
                    "type": "user_fact",
                    "key": key,
                    "value": value,
                    "source": msg.get("content", "")[:100]
                })

        # Generate corrections
        if reflection["outcome"] in ["failure", "neutral_accepted"]:
            reflection["corrections_needed"].append({
                "issue": "response_effectiveness",
                "suggestion": "Review similar successful sessions for better approach",
                "priority": "high" if reflection["outcome"] == "failure" else "medium"
            })

        # Apply reflection
        self.apply_reflection(reflection)
        return reflection
    
    def _extract_facts(self, content: str) -> Dict[str, str]:
        """Extract important facts from message."""
        facts = {}
        content_lower = content.lower()
        
        # Name patterns
        name_match = re.search(r"my name is (\w+)", content_lower)
        if name_match:
            facts["user_name"] = name_match.group(1)
        
        # Project patterns
        project_match = re.search(r"working on (\w+)", content_lower)
        if project_match:
            facts["current_project"] = project_match.group(1)
        
        return facts
    
    def apply_reflection(self, reflection: Dict):
        """
        Apply a reflection by:
        1. Storing memories
        2. Queuing improvements
        3. Updating user model
        """
        # Store memories
        for memory in reflection.get("memories_to_create", []):
            if memory["type"] == "user_fact":
                self.user_model._update_important_fact(
                    memory["key"],
                    memory["value"],
                    confidence=0.7
                )
        
        # Add memories to vector DB
        if reflection.get("memories_to_create"):
            for memory in reflection["memories_to_create"]:
                self.vector_db.add_memory(
                    content=f"{memory['key']}: {memory['value']}",
                    importance=0.7,
                    tags=["reflection", memory["type"]],
                    metadata={"reflection": True}
                )
        
        # Queue improvements
        for improvement in reflection.get("improvements_identified", []):
            if improvement["type"] in ["reinforce", "fix_needed"]:
                # Don't queue reinforces directly, just log them
                self.reflections["corrections_made"].append({
                    **improvement,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                self.improvements["pending"].append({
                    **improvement,
                    "identified_at": datetime.now().isoformat(),
                    "reflection_session": reflection.get("session_id")
                })
        
        # Keep recent reflections limited
        max_reflections = 100
        if len(self.reflections["session_reflections"]) > max_reflections:
            self.reflections["session_reflections"] = \
                self.reflections["session_reflections"][-max_reflections:]
        
        self.reflections["session_reflections"].append(reflection)
        self._save_reflections()
        self._save_improvements()
    
    def cross_session_reflection(self, days_back: int = 7) -> Dict:
        """
        Look for patterns across multiple recent sessions.
        
        Returns reflection on cross-session patterns.
        """
        recent_memories = self.vector_db.get_recent_memories(hours=days_back * 24, limit=200)
        
        cross_reflection = {
            "timestamp": datetime.now().isoformat(),
            "sessions_analyzed": len(set(m.get("session_id") for m in recent_memories)),
            "patterns_found": [],
            "recommendations": []
        }
        
        if cross_reflection["sessions_analyzed"] < 3:
            cross_reflection["note"] = "Not enough sessions for meaningful cross-session analysis"
            return cross_reflection
        
        # Group by session
        session_contents = {}
        for memory in recent_memories:
            sid = memory.get("session_id", "unknown")
            if sid not in session_contents:
                session_contents[sid] = []
            session_contents[sid].append(memory)
        
        # Find common themes across sessions
        all_topics = []
        for sid, memories in session_contents.items():
            for mem in memories:
                topics = self._extract_topics_from_content(mem.get("content", ""))
                all_topics.extend(topics)
        
        # Count topic frequency
        from collections import Counter
        topic_counts = Counter(all_topics)
        
        for topic, count in topic_counts.most_common(5):
            if count >= 3:
                cross_reflection["patterns_found"].append({
                    "pattern": f"topic_recurrence:{topic}",
                    "occurrences": count,
                    "significance": "User consistently asks about this topic"
                })
                
                cross_reflection["recommendations"].append({
                    "type": "topic_focus",
                    "topic": topic,
                    "action": f"Ensure we have good memory/context on {topic}"
                })
        
        # Look for repeated failed attempts
        failed_sessions = []
        for sid, memories in session_contents.items():
            has_frustration = any(
                "doesn't work" in m.get("content", "").lower() or "still" in m.get("content", "").lower()
                for m in memories
            )
            if has_frustration:
                failed_sessions.append(sid)
        
        if len(failed_sessions) >= 2:
            cross_reflection["patterns_found"].append({
                "pattern": "repeated_failures",
                "sessions": failed_sessions,
                "significance": "User had issues in multiple sessions"
            })
            
            cross_reflection["recommendations"].append({
                "type": "follow_up",
                "action": "Check in with user about ongoing issues"
            })
        
        self.reflections["cross_session_reflections"].append(cross_reflection)
        self._save_reflections()
        
        return cross_reflection
    
    def _extract_topics_from_content(self, content: str) -> List[str]:
        """Extract topics from content."""
        topics = []
        content_lower = content.lower()
        
        topic_keywords = {
            "coding": ["code", "function", "script", "debug", "api", "python"],
            "ai": ["ai", "model", "llm", "gpt", "hermes", "agent"],
            "project": ["project", "building", "creating", "working on"],
            "help": ["help", "how to", "can you", "need to"],
            "memory": ["remember", "forget", "recall", "remind"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def get_next_improvement(self) -> Optional[Dict]:
        """Get the next pending improvement to apply."""
        if not self.improvements["pending"]:
            return None
        
        # Sort by priority and age
        pending = sorted(
            self.improvements["pending"],
            key=lambda x: (
                0 if x.get("priority") == "high" else 1,
                x.get("identified_at", "")
            )
        )
        
        return pending[0]
    
    def complete_improvement(self, improvement: Dict):
        """Mark an improvement as completed."""
        if improvement in self.improvements["pending"]:
            self.improvements["pending"].remove(improvement)
            self.improvements["completed"].append({
                **improvement,
                "completed_at": datetime.now().isoformat()
            })
            self._save_improvements()
    
    def reject_improvement(self, improvement: Dict, reason: str):
        """Reject an improvement with a reason."""
        if improvement in self.improvements["pending"]:
            self.improvements["pending"].remove(improvement)
            self.improvements["rejected"].append({
                **improvement,
                "rejected_at": datetime.now().isoformat(),
                "reason": reason
            })
            self._save_improvements()
    
    def run_self_check(self) -> Dict:
        """
        Run a self-check reflection cycle.
        Returns a report of what was found and actions taken.
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "session_reflections_performed": 0,
            "cross_session_reflection_performed": False,
            "improvements_queued": 0,
            "improvements_completed": 0,
            "stats": {}
        }
        
        # Cross-session reflection (happens less frequently)
        if self._should_run_cross_session():
            cross_refl = self.cross_session_reflection()
            report["cross_session_reflection_performed"] = True
            report["cross_session_findings"] = cross_refl.get("patterns_found", [])
        
        # Process pending improvements
        next_imp = self.get_next_improvement()
        if next_imp:
            # Apply the improvement
            self._apply_improvement(next_imp)
            self.complete_improvement(next_imp)
            report["improvements_completed"] = 1
        
        report["stats"] = self.get_stats()
        report["completed_at"] = datetime.now().isoformat()
        
        return report
    
    def _should_run_cross_session(self) -> bool:
        """Determine if we should run cross-session reflection."""
        last = self.reflections.get("cross_session_reflections", [])
        if not last:
            return True
        
        last_time = datetime.fromisoformat(last[-1].get("timestamp", "2000-01-01"))
        # Run at most once per day
        return (datetime.now() - last_time).total_seconds() > 86400
    
    def _apply_improvement(self, improvement: Dict):
        """Apply a specific improvement."""
        imp_type = improvement.get("type")
        
        if imp_type == "knowledge_gap":
            # Queue for research
            gap_desc = improvement.get("description", "")
            self.vector_db.add_memory(
                content=f"Knowledge gap identified: {gap_desc}",
                importance=0.5,
                tags=["knowledge_gap", "research_needed"],
                metadata={"improvement": True}
            )
        elif imp_type == "topic_focus":
            # Ensure topic is well-represented in memory
            topic = improvement.get("topic")
            if topic:
                existing = self.vector_db.search(topic, n_results=1)
                if not existing:
                    self.vector_db.add_memory(
                        content=f"Important topic for user: {topic}",
                        importance=0.6,
                        tags=["user_interest", topic]
                    )
    
    def get_stats(self) -> Dict:
        """Get reflection engine statistics."""
        return {
            "total_session_reflections": len(self.reflections.get("session_reflections", [])),
            "cross_session_reflections": len(self.reflections.get("cross_session_reflections", [])),
            "corrections_made": len(self.reflections.get("corrections_made", [])),
            "pending_improvements": len(self.improvements.get("pending", [])),
            "completed_improvements": len(self.improvements.get("completed", [])),
            "rejected_improvements": len(self.improvements.get("rejected", [])),
            "user_model_stats": self.user_model.get_stats()
        }
