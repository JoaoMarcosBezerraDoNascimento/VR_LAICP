from mcp.server.fastmcp import FastMCP

class criar_servidor_mcp():

    mcp = FastMCP("Servidor_mcp")

    @mcp.tool()
    def somar(a: any, b: any) -> int:
        a = int(a)
        b = int(b)
        """
        """
        return a + b
    

    @mcp.tool()
    def chamar_especialista(nome):
        """
        Docstring for domar
        
        :param a: Description
        :param b: Description
        """
        return f"Chamado {nome} com sucesso!"
    
    mcp.run()

if __name__ == "__main__":
    criar_servidor_mcp()