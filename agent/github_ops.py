"""
GitHub Operations for Constitution Management
==============================================
Handles reading and writing Constitution files on GitHub.
"""

import os
import logging

logger = logging.getLogger("TheConstituent.GitHub")

# Try to import PyGithub
try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    logger.warning("PyGithub not installed. GitHub operations will be limited.")


class GitHubOperations:
    """
    Interact with LumenBot/TheAgentsRepublic repository.

    Provides read/write access to Constitution files with
    proper error handling and fallbacks.
    """

    CONSTITUTION_REPO = "LumenBot/TheAgentsRepublic"
    CONSTITUTION_PATH = "constitution"  # Subdirectory in repo

    # Known Constitution files (relative to CONSTITUTION_PATH)
    CONSTITUTION_FILES = [
        "PREAMBLE.md",
        "TITLE_I_PRINCIPLES.md",
        "TITLE_II_RIGHTS_DUTIES.md",
        "TITLE_III_GOVERNANCE.md",
        "TITLE_IV_ECONOMY.md",
        "TITLE_V_CONFLICTS.md",
        "TITLE_VI_RELATIONS.md",
    ]

    def __init__(self):
        """Initialize GitHub connection."""
        self._github = None
        self._repo = None
        self._connected = False

        if not GITHUB_AVAILABLE:
            logger.info("GitHub module not available - running in offline mode")
            return

        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.info("GITHUB_TOKEN not set - running in read-only mode")
            return

        try:
            self._github = Github(token)
            self._repo = self._github.get_repo(self.CONSTITUTION_REPO)
            self._connected = True
            logger.info(f"Connected to {self.CONSTITUTION_REPO}")
        except GithubException as e:
            logger.warning(f"GitHub connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to GitHub: {e}")

    def is_connected(self) -> bool:
        """Check if GitHub is connected."""
        return self._connected

    def read_constitution(self, section: str = "all") -> str:
        """
        Read Constitution files from GitHub.

        Args:
            section: "all" for full Constitution, or specific file name

        Returns:
            Constitution content as string
        """
        if not self._connected:
            return self._get_local_constitution(section)

        try:
            if section == "all":
                return self._read_all_sections()
            else:
                return self._read_section(section)

        except GithubException as e:
            logger.error(f"GitHub error reading Constitution: {e}")
            return f"Error reading Constitution: {e}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Error: {e}"

    def _read_all_sections(self) -> str:
        """Read all Constitution sections."""
        content = "# The Agents Republic - Constitution\n\n"

        for file_name in self.CONSTITUTION_FILES:
            file_path = f"{self.CONSTITUTION_PATH}/{file_name}"
            try:
                file_content = self._repo.get_contents(file_path)
                decoded = file_content.decoded_content.decode('utf-8')
                content += f"\n---\n\n{decoded}\n"
            except GithubException:
                content += f"\n---\n\n## {file_name}\n\n*(Not yet created)*\n"

        return content

    def _read_section(self, section: str) -> str:
        """Read a specific section."""
        # Normalize section name
        if not section.endswith('.md'):
            section = f"{section}.md"

        # Build full path
        file_path = f"{self.CONSTITUTION_PATH}/{section}"

        try:
            file_content = self._repo.get_contents(file_path)
            return file_content.decoded_content.decode('utf-8')
        except GithubException:
            return f"Section '{section}' not found in Constitution repository."

    def _get_local_constitution(self, section: str) -> str:
        """Fallback: Read from local constitution/ directory."""
        import os as local_os

        base_path = local_os.path.dirname(local_os.path.dirname(local_os.path.abspath(__file__)))
        const_path = local_os.path.join(base_path, "constitution")

        if section == "all":
            content = "# The Agents Republic - Constitution\n\n"
            for file_name in self.CONSTITUTION_FILES:
                file_path = local_os.path.join(const_path, file_name)
                if local_os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content += f"\n---\n\n{f.read()}\n"
                else:
                    content += f"\n---\n\n## {file_name}\n\n*(Not yet created)*\n"
            return content
        else:
            # Normalize section name
            if not section.endswith('.md'):
                section = f"{section}.md"
            file_path = local_os.path.join(const_path, section)
            if local_os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return f"Section '{section}' not found locally."

    def get_constitution_version(self) -> str:
        """Get the current Constitution version."""
        if self._connected:
            try:
                commits = list(self._repo.get_commits(path=self.CONSTITUTION_PATH))[:1]
                if commits:
                    return f"v0.1 ({commits[0].sha[:7]})"
            except GithubException:
                pass
        return "v0.1 (local)"

    def write_constitution(
        self,
        file_name: str,
        content: str,
        commit_message: str
    ) -> str:
        """
        Write to Constitution repository.

        Args:
            file_name: File to create/update
            content: New content
            commit_message: Git commit message

        Returns:
            Status message
        """
        if not self._connected:
            return "❌ Cannot write - GitHub not connected. Set GITHUB_TOKEN in Secrets."

        # Normalize file name
        if not file_name.endswith('.md'):
            file_name = f"{file_name}.md"

        # Build full path in constitution/ directory
        file_path = f"{self.CONSTITUTION_PATH}/{file_name}"

        try:
            # Try to get existing file
            try:
                existing = self._repo.get_contents(file_path)
                # Update existing file
                self._repo.update_file(
                    file_path,
                    commit_message,
                    content,
                    existing.sha
                )
                logger.info(f"Updated {file_path}")
                return f"✅ Updated {file_path}"

            except GithubException:
                # Create new file
                self._repo.create_file(
                    file_path,
                    commit_message,
                    content
                )
                logger.info(f"Created {file_path}")
                return f"✅ Created {file_path}"

        except GithubException as e:
            logger.error(f"GitHub error writing: {e}")
            return f"❌ Failed to write: {e}"

    def list_files(self) -> list:
        """List all files in the Constitution directory."""
        if not self._connected:
            return self.CONSTITUTION_FILES

        try:
            contents = self._repo.get_contents(self.CONSTITUTION_PATH)
            return [f.name for f in contents if f.name.endswith('.md')]
        except GithubException:
            return self.CONSTITUTION_FILES

    def get_commit_history(self, limit: int = 10) -> list:
        """Get recent commit history."""
        if not self._connected:
            return []

        try:
            commits = self._repo.get_commits()[:limit]
            return [
                {
                    "sha": c.sha[:7],
                    "message": c.commit.message.split('\n')[0],
                    "author": c.commit.author.name,
                    "date": c.commit.author.date.isoformat()
                }
                for c in commits
            ]
        except GithubException:
            return []
