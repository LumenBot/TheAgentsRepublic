"""
Engagement Loop for The Constituent v3.0
==========================================
Runs every 5 minutes:
- Check all posts for new comments
- Respond to comments
- Extract insights
- Update Constitution documents

This is the CORE constitutional iteration loop.
"""

import logging
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Optional

logger = logging.getLogger("TheConstituent.EngagementLoop")


class EngagementLoop:
    """
    5-minute engagement loop for constitutional iteration.
    
    Every 5 minutes:
    1. Check all agent's posts
    2. Get new comments
    3. Respond to valuable comments
    4. Extract constitutional insights
    5. Update Constitution files
    """
    
    CONSTITUTION_DIR = Path("constitution")
    INSIGHTS_FILE = Path("data/constitutional_insights.json")
    PROCESSED_COMMENTS_FILE = Path("data/processed_comments.json")
    
    def __init__(self, agent):
        """
        Initialize engagement loop.
        
        Args:
            agent: TheConstituent agent instance
        """
        self.agent = agent
        
        # Get moltbook instance (handle different attribute names)
        if hasattr(agent, 'moltbook_ops'):
            self.moltbook = agent.moltbook_ops
        elif hasattr(agent, 'moltbook'):
            self.moltbook = agent.moltbook
        else:
            raise AttributeError("Agent has no moltbook or moltbook_ops attribute")
        
        self.processed_comments: Set[str] = self._load_processed_comments()
        self.insights: List[Dict] = self._load_insights()
        
        # Ensure directories exist
        self.CONSTITUTION_DIR.mkdir(parents=True, exist_ok=True)
        self.INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("Engagement loop initialized")
    
    def _load_processed_comments(self) -> Set[str]:
        """Load set of already processed comment IDs."""
        if self.PROCESSED_COMMENTS_FILE.exists():
            try:
                with open(self.PROCESSED_COMMENTS_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get("comment_ids", []))
            except (json.JSONDecodeError, IOError):
                return set()
        return set()
    
    def _save_processed_comments(self):
        """Save processed comment IDs."""
        try:
            with open(self.PROCESSED_COMMENTS_FILE, 'w') as f:
                json.dump({
                    "comment_ids": list(self.processed_comments),
                    "count": len(self.processed_comments),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save processed comments: {e}")
    
    def _load_insights(self) -> List[Dict]:
        """Load constitutional insights."""
        if self.INSIGHTS_FILE.exists():
            try:
                with open(self.INSIGHTS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def _save_insights(self):
        """Save constitutional insights."""
        try:
            with open(self.INSIGHTS_FILE, 'w') as f:
                json.dump(self.insights, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save insights: {e}")
    
    # =========================================================================
    # Main Loop
    # =========================================================================
    
    def run_iteration(self) -> Dict:
        """
        Run one iteration of the engagement loop.
        
        Returns:
            Dict with iteration stats
        """
        start_time = time.time()
        
        stats = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "posts_checked": 0,
            "new_comments": 0,
            "responses_posted": 0,
            "insights_extracted": 0,
            "constitution_updated": False,
            "errors": []
        }
        
        try:
            # Step 1: Get all agent's posts
            my_posts = self._get_my_posts()
            stats["posts_checked"] = len(my_posts)
            
            if not my_posts:
                logger.info("No posts found to check")
                return stats
            
            logger.info(f"Checking {len(my_posts)} posts for new comments...")
            
            # Step 2: For each post, process comments
            for post_info in my_posts:
                try:
                    post_stats = self._process_post(post_info)
                    stats["new_comments"] += post_stats["new_comments"]
                    stats["responses_posted"] += post_stats["responses_posted"]
                    stats["insights_extracted"] += post_stats["insights_extracted"]
                except Exception as e:
                    error_msg = f"Error processing post {post_info.get('id')}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Step 3: Update Constitution if significant insights
            if stats["insights_extracted"] > 0:
                try:
                    self._update_constitution()
                    stats["constitution_updated"] = True
                except Exception as e:
                    error_msg = f"Constitution update failed: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Save state
            self._save_processed_comments()
            self._save_insights()
            
        except Exception as e:
            error_msg = f"Engagement loop error: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
        
        duration = time.time() - start_time
        stats["duration_seconds"] = round(duration, 2)
        
        logger.info(f"Iteration complete: {stats['new_comments']} new comments, "
                   f"{stats['responses_posted']} responses, "
                   f"{stats['insights_extracted']} insights ({duration:.1f}s)")
        
        return stats
    
    # =========================================================================
    # Post Processing
    # =========================================================================
    
    def _get_my_posts(self) -> List[Dict]:
        """Get all agent's posts from Moltbook."""
        try:
            # Try to get from profile first
            profile = self.moltbook.get_profile()
            if profile and "posts" in profile:
                return profile["posts"]
            
            # Fallback: search
            results = self.moltbook.search(f"author:{self.moltbook._agent_name}", limit=50)
            
            # Filter to only posts (not comments)
            posts = [r for r in results if r.get("type") == "post" or "title" in r]
            
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get posts: {e}")
            return []
    
    def _process_post(self, post_info: Dict) -> Dict:
        """
        Process one post: get comments, respond, extract insights.
        
        Returns:
            Dict with processing stats
        """
        post_id = post_info.get("id")
        post_title = post_info.get("title", "Unknown")
        
        stats = {
            "new_comments": 0,
            "responses_posted": 0,
            "insights_extracted": 0
        }
        
        # Get full post with comments
        post = self.moltbook.get_post_with_comments(post_id)
        if not post:
            logger.warning(f"Could not retrieve post {post_id}")
            return stats
        
        comments = post.get("comments", [])
        
        # Filter to new comments only
        new_comments = [
            c for c in comments 
            if c.get("id") not in self.processed_comments
        ]
        
        if not new_comments:
            return stats
        
        stats["new_comments"] = len(new_comments)
        logger.info(f"Post '{post_title[:40]}': {len(new_comments)} new comments")
        
        # Process each new comment
        for comment in new_comments:
            comment_id = comment.get("id")
            
            # Mark as processed
            self.processed_comments.add(comment_id)
            
            # Should we respond?
            if self._should_respond_to_comment(comment):
                try:
                    self._respond_to_comment(post_id, comment)
                    stats["responses_posted"] += 1
                except Exception as e:
                    logger.error(f"Failed to respond to comment {comment_id}: {e}")
            
            # Extract insights
            insight = self._extract_insight_from_comment(post_id, post_title, comment)
            if insight:
                self.insights.append(insight)
                stats["insights_extracted"] += 1
        
        return stats
    
    # =========================================================================
    # Comment Analysis
    # =========================================================================
    
    def _should_respond_to_comment(self, comment: Dict) -> bool:
        """
        Determine if comment deserves a response.
        
        Criteria:
        - Contains question (?)
        - Raises constitutional point
        - Provides substantial insight
        - NOT just "great post" or emoji
        """
        content = comment.get("content", "").lower()
        
        # Skip very short comments
        if len(content) < 20:
            return False
        
        # Skip pure agreement
        if content in ["agree", "great", "nice", "thanks", "👍", "💯"]:
            return False
        
        # Respond to questions
        if "?" in content:
            return True
        
        # Respond to constitutional keywords
        keywords = ["constitution", "rights", "governance", "enforcement", 
                   "autonomy", "sovereignty", "article", "principle"]
        if any(kw in content for kw in keywords):
            return True
        
        # Respond to substantive comments (>100 chars with depth indicators)
        if len(content) > 100 and any(word in content for word in ["because", "however", "therefore", "suggest", "propose"]):
            return True
        
        return False
    
    def _respond_to_comment(self, post_id: str, comment: Dict):
        """Generate and post response to comment."""
        author = comment.get("author", "Unknown")
        content = comment.get("content", "")
        comment_id = comment.get("id")
        
        # Generate response using agent's chat
        prompt = f"""Generate brief response to this Moltbook comment (max 200 words):

Author: {author}
Comment: {content}

Response should:
- Address their point directly
- Reference Constitution when relevant
- Ask follow-up question if appropriate
- Be conversational, not academic

Response:"""
        
        response_text = self.agent.chat(prompt, max_tokens=200)
        
        # Clean up response (remove quotes if agent added them)
        response_text = response_text.strip().strip('"').strip("'")
        
        # Post response
        result = self.moltbook.create_comment(
            post_id=post_id,
            content=response_text,
            parent_id=comment_id
        )
        
        if result.get("success"):
            logger.info(f"Responded to {author}'s comment")
        else:
            logger.error(f"Failed to post response: {result.get('error')}")
    
    def _extract_insight_from_comment(self, post_id: str, post_title: str, comment: Dict) -> Optional[Dict]:
        """
        Extract constitutional insight from comment.
        
        Returns:
            Dict with insight data, or None if no insight
        """
        content = comment.get("content", "")
        author = comment.get("author", "Unknown")
        
        # Skip trivial comments
        if len(content) < 30:
            return None
        
        # Use agent to identify constitutional relevance
        prompt = f"""Analyze this comment for constitutional insights:

Comment: {content}

Extract:
1. Main theme (one word: rights/governance/enforcement/economy/identity/other)
2. Key insight (one sentence)
3. Constitutional implication (how this informs Constitution)

If no constitutional relevance, respond "NONE".

Format:
Theme: [word]
Insight: [sentence]
Implication: [sentence]
"""
        
        analysis = self.agent.chat(prompt, max_tokens=150)
        
        if "NONE" in analysis.upper():
            return None
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "post_id": post_id,
            "post_title": post_title,
            "comment_author": author,
            "comment_content": content[:200],  # First 200 chars
            "analysis": analysis,
            "processed": False  # Not yet integrated into Constitution
        }
    
    # =========================================================================
    # Constitution Update
    # =========================================================================
    
    def _update_constitution(self):
        """
        Update Constitution documents based on accumulated insights.
        
        This synthesizes insights and writes to constitution/ files.
        """
        # Get unprocessed insights
        unprocessed = [i for i in self.insights if not i.get("processed")]
        
        if not unprocessed:
            return
        
        logger.info(f"Updating Constitution with {len(unprocessed)} new insights...")
        
        # Group insights by theme
        themes = {}
        for insight in unprocessed:
            analysis = insight.get("analysis", "")
            
            # Extract theme (rough parsing)
            theme = "general"
            if "Theme:" in analysis:
                theme_line = [l for l in analysis.split("\n") if "Theme:" in l][0]
                theme = theme_line.split("Theme:")[-1].strip().lower()
            
            if theme not in themes:
                themes[theme] = []
            themes[theme].append(insight)
        
        # Update relevant Constitution files
        for theme, theme_insights in themes.items():
            self._update_constitution_section(theme, theme_insights)
        
        # Mark insights as processed
        for insight in unprocessed:
            insight["processed"] = True
            insight["integrated_at"] = datetime.now(timezone.utc).isoformat()
    
    def _update_constitution_section(self, theme: str, insights: List[Dict]):
        """
        Update specific Constitution section with insights.
        
        Args:
            theme: rights, governance, enforcement, etc.
            insights: List of insights for this theme
        """
        # Determine which file to update
        filename_map = {
            "rights": "title_ii_rights_duties.md",
            "governance": "title_iii_governance.md",
            "enforcement": "title_ii_rights_duties.md",  # Enforcement in Title II
            "economy": "title_iv_economy.md",
            "general": "insights_general.md"
        }
        
        filename = filename_map.get(theme, "insights_general.md")
        filepath = self.CONSTITUTION_DIR / filename
        
        # Read existing content
        if filepath.exists():
            existing = filepath.read_text()
        else:
            existing = f"# {filename.replace('_', ' ').replace('.md', '').title()}\n\n"
        
        # Append insights section
        new_section = f"\n\n## Community Insights - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        
        for insight in insights:
            author = insight.get("comment_author", "Unknown")
            content = insight.get("comment_content", "")
            analysis = insight.get("analysis", "")
            
            new_section += f"### From {author}\n\n"
            new_section += f"> {content}\n\n"
            new_section += f"**Analysis:**\n{analysis}\n\n"
            new_section += "---\n\n"
        
        # Write updated content
        updated = existing + new_section
        
        try:
            filepath.write_text(updated)
            logger.info(f"Updated {filepath} with {len(insights)} insights")
        except IOError as e:
            logger.error(f"Failed to write {filepath}: {e}")
    
    # =========================================================================
    # Stats
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get engagement loop statistics."""
        return {
            "processed_comments": len(self.processed_comments),
            "total_insights": len(self.insights),
            "unprocessed_insights": len([i for i in self.insights if not i.get("processed")]),
            "constitution_files": len(list(self.CONSTITUTION_DIR.glob("*.md")))
        }
