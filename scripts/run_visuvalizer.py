from supplychainlens.graph import GraphLoader, render_ascii_subgraph

def main():
	g = GraphLoader().load()
	print(render_ascii_subgraph(g, "npm:express@5.2.0", max_depth=3))

if __name__ == "__main__":
    main()