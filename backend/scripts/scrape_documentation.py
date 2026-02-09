#!/usr/bin/env python3
"""
Documentation scraper for framework documentation.

This script downloads and parses documentation from various frameworks
including NestJS, React, FastAPI, Spring Boot, .NET Core, Vue.js, Angular,
Django, and Express.js. The documentation is chunked into manageable pieces
for embedding generation.

Usage:
    python scrape_documentation.py --framework nestjs --output docs/nestjs
    python scrape_documentation.py --all --output docs/
"""

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@dataclass
class DocumentChunk:
    """Represents a chunk of documentation."""
    content: str
    source: str
    framework: str
    section: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict] = None


class FrameworkScraper:
    """Base class for framework documentation scrapers."""
    
    def __init__(self, framework: str, base_url: str, version: Optional[str] = None):
        self.framework = framework
        self.base_url = base_url
        self.version = version
        self.session: Optional[aiohttp.ClientSession] = None
        self.visited_urls = set()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single page content."""
        if url in self.visited_urls:
            return None
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    self.visited_urls.add(url)
                    return await response.text()
                else:
                    print(f"⚠ Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            print(f"⚠ Error fetching {url}: {e}")
            return None
    
    def chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """
        Split text into chunks of approximately max_chunk_size characters.
        Tries to split on paragraph boundaries.
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def scrape(self) -> List[DocumentChunk]:
        """Scrape documentation. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement scrape()")



class NestJSScraper(FrameworkScraper):
    """Scraper for NestJS documentation."""
    
    def __init__(self, version: Optional[str] = None):
        super().__init__("NestJS", "https://docs.nestjs.com", version or "10.x")
        self.doc_pages = [
            "/",
            "/controllers",
            "/providers",
            "/modules",
            "/middleware",
            "/exception-filters",
            "/pipes",
            "/guards",
            "/interceptors",
            "/custom-decorators",
            "/fundamentals/dependency-injection",
            "/fundamentals/async-providers",
            "/fundamentals/circular-dependency",
            "/fundamentals/module-reference",
            "/techniques/database",
            "/techniques/validation",
            "/techniques/caching",
            "/techniques/serialization",
            "/techniques/configuration",
            "/security/authentication",
            "/security/authorization",
            "/graphql/quick-start",
            "/websockets/gateways",
            "/microservices/basics",
        ]
    
    async def scrape(self) -> List[DocumentChunk]:
        """Scrape NestJS documentation."""
        chunks = []
        
        for page_path in self.doc_pages:
            url = urljoin(self.base_url, page_path)
            html = await self.fetch_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract main content
            content_div = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
            
            if not content_div:
                continue
            
            # Extract text content
            text = content_div.get_text(separator='\n', strip=True)
            
            # Clean up text
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            # Extract section name from URL
            section = page_path.strip('/').replace('/', ' > ').title() or "Introduction"
            
            # Chunk the text
            text_chunks = self.chunk_text(text)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    content=chunk_text,
                    source=url,
                    framework=self.framework,
                    section=section,
                    version=self.version,
                    metadata={"chunk_index": i, "total_chunks": len(text_chunks)}
                )
                chunks.append(chunk)
            
            print(f"✓ Scraped {url} ({len(text_chunks)} chunks)")
        
        return chunks



class ReactScraper(FrameworkScraper):
    """Scraper for React documentation."""
    
    def __init__(self, version: Optional[str] = None):
        super().__init__("React", "https://react.dev", version or "18.x")
        self.doc_pages = [
            "/learn",
            "/learn/thinking-in-react",
            "/learn/describing-the-ui",
            "/learn/adding-interactivity",
            "/learn/managing-state",
            "/learn/escape-hatches",
            "/reference/react",
            "/reference/react/hooks",
            "/reference/react/useState",
            "/reference/react/useEffect",
            "/reference/react/useContext",
            "/reference/react/useReducer",
            "/reference/react/useCallback",
            "/reference/react/useMemo",
            "/reference/react/useRef",
            "/reference/react-dom",
            "/reference/react-dom/components",
        ]
    
    async def scrape(self) -> List[DocumentChunk]:
        """Scrape React documentation."""
        chunks = []
        
        for page_path in self.doc_pages:
            url = urljoin(self.base_url, page_path)
            html = await self.fetch_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract main content
            content_div = soup.find('article') or soup.find('main')
            
            if not content_div:
                continue
            
            # Remove code blocks temporarily to extract text
            text = content_div.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            section = page_path.strip('/').replace('/', ' > ').title() or "Introduction"
            
            text_chunks = self.chunk_text(text)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    content=chunk_text,
                    source=url,
                    framework=self.framework,
                    section=section,
                    version=self.version,
                    metadata={"chunk_index": i, "total_chunks": len(text_chunks)}
                )
                chunks.append(chunk)
            
            print(f"✓ Scraped {url} ({len(text_chunks)} chunks)")
        
        return chunks



class FastAPIScraper(FrameworkScraper):
    """Scraper for FastAPI documentation."""
    
    def __init__(self, version: Optional[str] = None):
        super().__init__("FastAPI", "https://fastapi.tiangolo.com", version or "0.100+")
        self.doc_pages = [
            "/",
            "/tutorial/first-steps/",
            "/tutorial/path-params/",
            "/tutorial/query-params/",
            "/tutorial/body/",
            "/tutorial/query-params-str-validations/",
            "/tutorial/path-params-numeric-validations/",
            "/tutorial/body-multiple-params/",
            "/tutorial/body-fields/",
            "/tutorial/body-nested-models/",
            "/tutorial/dependencies/",
            "/tutorial/security/",
            "/tutorial/middleware/",
            "/tutorial/cors/",
            "/tutorial/sql-databases/",
            "/tutorial/bigger-applications/",
            "/tutorial/background-tasks/",
            "/advanced/",
            "/advanced/path-operation-advanced-configuration/",
            "/advanced/additional-status-codes/",
            "/advanced/response-directly/",
            "/advanced/custom-response/",
            "/advanced/websockets/",
        ]
    
    async def scrape(self) -> List[DocumentChunk]:
        """Scrape FastAPI documentation."""
        chunks = []
        
        for page_path in self.doc_pages:
            url = urljoin(self.base_url, page_path)
            html = await self.fetch_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            content_div = soup.find('article') or soup.find('main') or soup.find('div', class_='md-content')
            
            if not content_div:
                continue
            
            text = content_div.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            section = page_path.strip('/').replace('/', ' > ').title() or "Introduction"
            
            text_chunks = self.chunk_text(text)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    content=chunk_text,
                    source=url,
                    framework=self.framework,
                    section=section,
                    version=self.version,
                    metadata={"chunk_index": i, "total_chunks": len(text_chunks)}
                )
                chunks.append(chunk)
            
            print(f"✓ Scraped {url} ({len(text_chunks)} chunks)")
        
        return chunks



class GenericScraper(FrameworkScraper):
    """Generic scraper for other frameworks with simple documentation structure."""
    
    def __init__(self, framework: str, base_url: str, doc_pages: List[str], version: Optional[str] = None):
        super().__init__(framework, base_url, version)
        self.doc_pages = doc_pages
    
    async def scrape(self) -> List[DocumentChunk]:
        """Scrape documentation using generic approach."""
        chunks = []
        
        for page_path in self.doc_pages:
            url = urljoin(self.base_url, page_path)
            html = await self.fetch_page(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple selectors for content
            content_div = (
                soup.find('article') or 
                soup.find('main') or 
                soup.find('div', class_='content') or
                soup.find('div', class_='markdown') or
                soup.find('div', class_='documentation')
            )
            
            if not content_div:
                continue
            
            text = content_div.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            section = page_path.strip('/').replace('/', ' > ').title() or "Introduction"
            
            text_chunks = self.chunk_text(text)
            
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    content=chunk_text,
                    source=url,
                    framework=self.framework,
                    section=section,
                    version=self.version,
                    metadata={"chunk_index": i, "total_chunks": len(text_chunks)}
                )
                chunks.append(chunk)
            
            print(f"✓ Scraped {url} ({len(text_chunks)} chunks)")
        
        return chunks


# Framework configurations
FRAMEWORK_CONFIGS = {
    "nestjs": lambda: NestJSScraper(),
    "react": lambda: ReactScraper(),
    "fastapi": lambda: FastAPIScraper(),
    "django": lambda: GenericScraper(
        "Django",
        "https://docs.djangoproject.com/en/stable/",
        [
            "intro/tutorial01/", "intro/tutorial02/", "intro/tutorial03/",
            "topics/db/models/", "topics/db/queries/", "topics/http/views/",
            "topics/forms/", "topics/auth/", "topics/cache/", "topics/signals/",
            "ref/models/fields/", "ref/views/", "ref/middleware/",
        ],
        "4.x"
    ),
    "express": lambda: GenericScraper(
        "Express.js",
        "https://expressjs.com",
        [
            "/en/starter/installing.html", "/en/starter/hello-world.html",
            "/en/guide/routing.html", "/en/guide/middleware.html",
            "/en/guide/error-handling.html", "/en/guide/database-integration.html",
            "/en/advanced/best-practice-security.html",
        ],
        "4.x"
    ),
    "vue": lambda: GenericScraper(
        "Vue.js",
        "https://vuejs.org",
        [
            "/guide/introduction.html", "/guide/essentials/application.html",
            "/guide/essentials/template-syntax.html", "/guide/essentials/reactivity-fundamentals.html",
            "/guide/essentials/computed.html", "/guide/essentials/conditional.html",
            "/guide/essentials/list.html", "/guide/essentials/event-handling.html",
            "/guide/components/registration.html", "/guide/components/props.html",
            "/guide/reusability/composables.html",
        ],
        "3.x"
    ),
    "angular": lambda: GenericScraper(
        "Angular",
        "https://angular.io",
        [
            "/guide/what-is-angular", "/guide/component-overview",
            "/guide/template-syntax", "/guide/lifecycle-hooks",
            "/guide/dependency-injection", "/guide/hierarchical-dependency-injection",
            "/guide/routing-overview", "/guide/forms-overview",
            "/guide/http", "/guide/observables",
        ],
        "17.x"
    ),
    "spring": lambda: GenericScraper(
        "Spring Boot",
        "https://docs.spring.io/spring-boot/docs/current/reference/html/",
        [
            "getting-started.html", "using.html#using.build-systems",
            "web.html#web.servlet", "data.html#data.sql",
            "io.html#io.rest-client", "messaging.html",
            "actuator.html", "howto.html",
        ],
        "3.x"
    ),
    "dotnet": lambda: GenericScraper(
        ".NET Core",
        "https://learn.microsoft.com/en-us/aspnet/core",
        [
            "/introduction-to-aspnet-core", "/fundamentals/",
            "/mvc/overview", "/web-api/", "/data/ef-mvc/",
            "/security/authentication/", "/performance/caching/",
            "/host-and-deploy/", "/tutorials/first-web-api",
        ],
        "8.x"
    ),
}



async def scrape_framework(framework: str, output_dir: Path) -> List[DocumentChunk]:
    """Scrape documentation for a specific framework."""
    if framework not in FRAMEWORK_CONFIGS:
        print(f"❌ Unknown framework: {framework}")
        print(f"   Available frameworks: {', '.join(FRAMEWORK_CONFIGS.keys())}")
        return []
    
    print(f"\n{'='*60}")
    print(f"SCRAPING {framework.upper()} DOCUMENTATION")
    print(f"{'='*60}\n")
    
    scraper = FRAMEWORK_CONFIGS[framework]()
    
    async with scraper:
        chunks = await scraper.scrape()
    
    # Save chunks to JSON file
    output_file = output_dir / f"{framework}_docs.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    chunks_data = [
        {
            "content": chunk.content,
            "source": chunk.source,
            "framework": chunk.framework,
            "section": chunk.section,
            "version": chunk.version,
            "metadata": chunk.metadata or {}
        }
        for chunk in chunks
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(chunks)} chunks to {output_file}")
    
    return chunks


async def scrape_all_frameworks(output_dir: Path) -> Dict[str, List[DocumentChunk]]:
    """Scrape documentation for all supported frameworks."""
    all_chunks = {}
    
    for framework in FRAMEWORK_CONFIGS.keys():
        chunks = await scrape_framework(framework, output_dir)
        all_chunks[framework] = chunks
    
    return all_chunks


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape framework documentation for AI Agent System"
    )
    parser.add_argument(
        "--framework",
        type=str,
        choices=list(FRAMEWORK_CONFIGS.keys()) + ["all"],
        help="Framework to scrape (or 'all' for all frameworks)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/scraped",
        help="Output directory for scraped documentation"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scrape all frameworks"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    
    if args.all or args.framework == "all":
        print("\n" + "="*60)
        print("SCRAPING ALL FRAMEWORK DOCUMENTATION")
        print("="*60)
        asyncio.run(scrape_all_frameworks(output_dir))
    elif args.framework:
        asyncio.run(scrape_framework(args.framework, output_dir))
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python scrape_documentation.py --framework nestjs")
        print("  python scrape_documentation.py --all")
        return 1
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print("="*60)
    print(f"\nDocumentation saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Review scraped documentation in output directory")
    print("2. Run embedding generation: python ingest_documentation.py")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
