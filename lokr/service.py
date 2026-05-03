"""
LokrService - clean wrapper around Lokr internal modules.
Provides traceable, rich data structures for agent consumption.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any


class LokrService:
    """
    Provides a simplified, agent-friendly interface to Lokr's Graph-RAG engine.
    All returned data preserves full graph node IDs and metadata for iterative reasoning.
    """

    def __init__(self, project_path: str, lokr_path: Optional[str] = None):
        # Resolve Lokr path
        if lokr_path is None:
            lokr_path = os.environ.get("LOKR_PATH", "../Lokr")
        self.lokr_path = os.path.abspath(lokr_path)
        self.project_path = os.path.abspath(project_path)

        # Ensure Lokr is importable
        if self.lokr_path not in sys.path:
            sys.path.insert(0, self.lokr_path)

        self.initialized = False
        self.oracle = None
        self.parser = None
        self.graph = None
        self.vector_db = None

        try:
            from engine.oracle import ContextOracle
            from core.parser import CodeParser
            from core.graph import DependencyGraph
            from data.vector_db import CodebaseVectorDB
        except ImportError as e:
            print(f"Error importing from Lokr: {e}")
            print(f"Ensure the Lokr project is available at: {self.lokr_path}")
            return

        # Initialize Parser
        try:
            self.parser = CodeParser()
        except Exception as e:
            print(f"Failed to initialize CodeParser: {e}")
            return

        # Load dependency graph
        try:
            graph_file = Path(self.project_path) / ".lokr" / "graph.json"
            self.graph = DependencyGraph()
            self.graph.load_graph(graph_file)
        except Exception as e:
            print(f"Failed to load dependency graph: {e}")
            return

        # Initialize ChromaDB vector store (exactly as Lokr does)
        try:
            db_dir = Path(self.project_path) / "data" / "vector_store"
            self.vector_db = CodebaseVectorDB(db_dir=str(db_dir))
        except Exception as e:
            print(f"Failed to initialize CodebaseVectorDB: {e}")
            return

        # Initialize ContextOracle
        try:
            self.oracle = ContextOracle(
                parser=self.parser,
                graph=self.graph,
                db=self.vector_db,
                graph_path=str(Path(self.project_path) / ".lokr" / "graph.json"),
                project_root=Path(self.project_path),
            )
        except Exception as e:
            print(f"Failed to initialize ContextOracle: {e}")
            return

        self.initialized = True
        print(f"LokrService initialized for project: {self.project_path}")

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def search_code(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search over the codebase. Returns full node data for each hit.
        """
        if not self.initialized:
            return []
        try:
            retriever = getattr(self.oracle, 'retriever', None)
            if retriever is None:
                return []
            # search_and_expand returns a tuple: (initial_hits, expanded_hits)
            initial_hits, expanded_hits = retriever.search_and_expand(query, top_k)
            # Combine both sets of node IDs
            node_ids = initial_hits.union(expanded_hits)
            results = []
            for nid in node_ids:
                node_data = self.graph.graph.nodes.get(nid, {})
                entry = {"node_id": nid, **node_data}
                results.append(entry)
            return results
        except Exception as e:
            print(f"search_code failed: {e}")
            return []

    def get_file_summary(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file and return its structure (imports, functions, classes, etc.).
        """
        if not self.initialized:
            return {"error": "LokrService not initialized"}
        resolved = file_path
        if not os.path.isabs(file_path):
            resolved = os.path.join(self.project_path, file_path)
        if not os.path.exists(resolved):
            return {"error": "File not found", "file_path": resolved}
        try:
            data = self.parser.parse_file(resolved)
            data["file_path"] = resolved
            return data
        except Exception as e:
            return {"error": str(e), "file_path": resolved}

    def get_function_dependencies(self, func_name: str) -> Dict[str, Any]:
        """
        Find a function node by name and return its callers and callees.
        Each caller/callee includes full node data and node_id.
        """
        if not self.initialized:
            return {"error": "LokrService not initialized", "function_name": func_name}

        candidates = []
        for nid, ndata in self.graph.graph.nodes(data=True):
            ntype = ndata.get('type') or ndata.get('node_type', '')
            if ntype in ('function', 'method') and ndata.get('name') == func_name:
                candidates.append(nid)

        if not candidates:
            for nid, ndata in self.graph.graph.nodes(data=True):
                ntype = ndata.get('type') or ndata.get('node_type', '')
                name = ndata.get('name', '')
                if ntype in ('function', 'method') and func_name in name:
                    candidates.append(nid)

        if not candidates:
            return {"error": "Function not found", "function_name": func_name}

        target = candidates[0]
        target_data = dict(self.graph.graph.nodes[target])

        callers = []
        for pred in self.graph.graph.predecessors(target):
            edge_data = self.graph.graph.get_edge_data(pred, target)
            if edge_data and edge_data.get('type') == 'calls':
                callers.append({"node_id": pred, **self.graph.graph.nodes[pred]})

        callees = []
        for succ in self.graph.graph.successors(target):
            edge_data = self.graph.graph.get_edge_data(target, succ)
            if edge_data and edge_data.get('type') == 'calls':
                callees.append({"node_id": succ, **self.graph.graph.nodes[succ]})

        return {
            "function_name": func_name,
            "node_id": target,
            "node_data": target_data,
            "callers": callers,
            "callees": callees,
        }

    def get_relevant_context(self, query: str, top_k: int = 10) -> str:
        """
        Returns Markdown context assembled by Lokr's ContextOracle.
        """
        if not self.initialized:
            return ""
        try:
            # generate_context returns a tuple: (markdown_string, center_nodes_set, expanded_node_ids_set)
            markdown_content, _, _ = self.oracle.generate_context(query, top_k)
            return markdown_content
        except Exception as e:
            print(f"get_relevant_context failed: {e}")
            return ""

    def get_project_summary(self) -> Dict[str, int]:
        """
        Count of file, function, class, variable, schema nodes in the graph.
        """
        if not self.initialized:
            return {}
        counts = {"file": 0, "function": 0, "method": 0, "class": 0, "variable": 0, "schema": 0}
        for _, ndata in self.graph.graph.nodes(data=True):
            ntype = ndata.get('type') or ndata.get('node_type', '')
            if ntype in counts:
                counts[ntype] += 1
        counts["function"] += counts.pop("method", 0)
        return counts

    def resolve_request(self, request: str) -> dict:
        """
        Interprets a natural-language request (e.g., "get dependencies of tokenRefresh")
        and calls the appropriate existing method using simple keyword matching.
        """
        req_lower = request.lower()
        words = request.split()
        
        # 1. Dependency request
        if "dependenc" in req_lower or "caller" in req_lower or "callee" in req_lower:
            func_name = ""
            if "of" in req_lower:
                try:
                    idx = req_lower.split().index("of")
                    func_name = words[idx + 1].strip("'\"")
                except ValueError:
                    pass
            if not func_name:
                func_name = words[-1].strip("'\"")
            
            if func_name:
                return self.get_function_dependencies(func_name)
        
        # 2. File summary request
        if "file" in req_lower or "summary" in req_lower:
            file_path = ""
            for word in words:
                if "." in word or "/" in word:
                    file_path = word.strip("'\"")
                    break
            if not file_path and "of" in req_lower:
                try:
                    idx = req_lower.split().index("of")
                    file_path = words[idx + 1].strip("'\"")
                except ValueError:
                    pass
            if not file_path:
                file_path = words[-1].strip("'\"")
                
            if file_path:
                return self.get_file_summary(file_path)
                
        # 3. Fallback to generic semantic search
        results = self.search_code(request)
        return {"query": request, "search_results": results}
