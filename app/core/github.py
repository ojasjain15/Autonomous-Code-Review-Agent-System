from github import Github
from typing import List, Dict, Optional, Tuple
import base64
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
from ..logger_config import get_logger

load_dotenv()

class GithubClient:
    
    def __init__(self, token: Optional[str] = None):
        self.logger = get_logger("github_client_1", "github_client_1.log")
        self.token = token or os.getenv("GITHUB_TOKEN")
        
        try:
            if not self.token:
                self.logger.warning("No GitHub token provided. Using unauthenticated client.", 
                                  extra={"authentication": "unauthenticated"})
                self.github = Github()
            else:
                self.logger.info("Initializing GitHub client with token", 
                               extra={"authentication": "token"})
                self.github = Github(self.token)
                
        except Exception as e:
            self.logger.error("Failed to initialize GitHub client", 
                            extra={
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            })
            raise

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        try:
            parts = urlparse(repo_url).path.strip('/').split('/')
            if len(parts) < 2:
                raise ValueError("Invalid repository URL format")
            
            owner, repo_name = parts[-2], parts[-1]
            self.logger.debug("Successfully parsed repository URL", 
                            extra={
                                "owner": owner,
                                "repo_name": repo_name,
                                "url": repo_url
                            })
            return owner, repo_name
            
        except Exception as e:
            self.logger.error("Failed to parse repository URL", 
                            extra={
                                "url": repo_url,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            })
            raise ValueError(f"Invalid repository URL: {repo_url}")

    def _get_file_content(self, repo, file_path: str, ref: str) -> Optional[str]:
        try:
            content = repo.get_contents(file_path, ref=ref)
            decoded_content = base64.b64decode(content.content).decode('utf-8')
            
            self.logger.debug("Successfully retrieved file content", 
                            extra={
                                "file_path": file_path,
                                "ref": ref,
                                "size": len(decoded_content)
                            })
            return decoded_content
            
        except Exception as e:
            self.logger.error("Failed to retrieve file content", 
                            extra={
                                "file_path": file_path,
                                "ref": ref,
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            })
            return None

    def get_pr_files(self, repo_url: str, pr_number: int) -> List[Dict]:
        self.logger.info("Starting PR files fetch", 
                        extra={
                            "pr_number": pr_number,
                            "repo_url": repo_url
                        })
        
        try:
            owner, repo_name = self._parse_repo_url(repo_url)
            repo_full_name = f"{owner}/{repo_name}"
            
            self.logger.debug("Getting repository", 
                            extra={"repo_full_name": repo_full_name})
            repo = self.github.get_repo(repo_full_name)
            
            self.logger.debug("Getting pull request", 
                            extra={"pr_number": pr_number})
            pull = repo.get_pull(pr_number)
            
            files = []
            failed_files = 0
            
            for file in pull.get_files():
                self.logger.debug("Processing PR file", 
                                extra={"file_path": file.filename})
                
                content = self._get_file_content(repo, file.filename, pull.head.sha)
                
                if content is not None:
                    files.append({
                        "name": file.filename,
                        "content": content,
                        "patch": file.patch
                    })
                else:
                    failed_files += 1
            
            self.logger.info("Completed PR files fetch", 
                           extra={
                               "total_files": len(files),
                               "failed_files": failed_files,
                               "pr_number": pr_number,
                               "repo": repo_full_name
                           })
            
            return files
            
        except Exception as e:
            error_message = str(e)
            self.logger.error("Failed to fetch PR files", 
                            extra={
                                "pr_number": pr_number,
                                "repo_url": repo_url,
                                "error_type": type(e).__name__,
                                "error_message": error_message
                            })
            raise Exception(f"Error fetching PR files: {error_message}")

    def cleanup(self):
        try:
            self.github.close()
            self.logger.info("Successfully cleaned up GitHub client")
        except Exception as e:
            self.logger.error("Failed to cleanup GitHub client", 
                            extra={
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            })
