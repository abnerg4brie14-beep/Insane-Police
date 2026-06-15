import discord
from discord.ext import commands
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Arquivo para armazenar dados de bate-ponto
DATA_FILE = 'bate_ponto_data.json'

# Hierarquia de cargos com emojis
HIERARQUIA_CARGOS = [
    ("Coronel", "🎖️", discord.Color.gold()),
    ("Tenente coronel", "🎖️", discord.Color.gold()),
    ("Major", "⭐", discord.Color.gold()),
    ("Capitão", "⭐", discord.Color.orange()),
    ("1 tenente", "🔶", discord.Color.orange()),
    ("2 tenente", "🔶", discord.Color.orange()),
    ("Aspirante oficial", "◽", discord.Color.from_rgb(200, 200, 200)),
    ("Sub tenente", "◾", discord.Color.from_rgb(150, 150, 150)),
    ("1 sargento", "▪️", discord.Color.from_rgb(100, 100, 100)),
    ("2 sargento", "▪️", discord.Color.from_rgb(100, 100, 100)),
    ("3 sargento", "▪️", discord.Color.from_rgb(100, 100, 100)),
    ("Cabo", "📍", discord.Color.blue()),
    ("Soldado", "🔵", discord.Color.blue()),
    ("Recruta", "⚪", discord.Color.light_grey()),
]

CARGO_EMOJI = {cargo: emoji for cargo, emoji, _ in HIERARQUIA_CARGOS}
CARGO_COR = {cargo: cor for cargo, _, cor in HIERARQUIA_CARGOS}

def carregar_dados():
    """Carrega dados do arquivo JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_dados(dados):
    """Salva dados no arquivo JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def obter_cargo_usuario(member):
    """Obtém o cargo principal do usuário"""
    if not member.roles:
        return "Sem cargo"
    for role in reversed(member.roles):
        if role.name != "@everyone":
            return role.name
    return "Sem cargo"

def obter_emoji_cargo(cargo):
    """Retorna o emoji do cargo"""
    return CARGO_EMOJI.get(cargo, "❓")

def obter_cor_cargo(cargo):
    """Retorna a cor do cargo"""
    return CARGO_COR.get(cargo, discord.Color.default())

# Criar instância do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ===== VIEWS (BOTÕES) =====
class BaterPontoView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.timeout = 300  # 5 minutos

    @discord.ui.button(label="✅ BATER PONTO", style=discord.ButtonStyle.green)
    async def bater_ponto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar se quem clicou é o mesmo que pediu
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem pediu pode usar este botão!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        user_name = interaction.user.name
        cargo = obter_cargo_usuario(interaction.user)
        emoji_cargo = obter_emoji_cargo(cargo)
        horario = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        dados = carregar_dados()
        
        if user_id not in dados:
            dados[user_id] = {
                'nome': user_name,
                'cargo': cargo,
                'registros': []
            }
        else:
            dados[user_id]['cargo'] = cargo
        
        registros = dados[user_id]['registros']
        if registros and registros[-1].get('saida') is None:
            embed = discord.Embed(
                title='❌ Erro',
                description=f'{interaction.user.mention}, você já está em serviço!\nUse o botão "SAIR DO SERVIÇO" para sair.',
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        dados[user_id]['registros'].append({
            'entrada': horario,
            'saida': None
        })
        
        salvar_dados(dados)
        
        embed = discord.Embed(
            title=f'✅ Entrada Registrada {emoji_cargo}',
            description=f'{interaction.user.mention} entrou em serviço',
            color=obter_cor_cargo(cargo)
        )
        embed.add_field(name='🕐 Horário', value=horario, inline=False)
        embed.add_field(name='👤 Usuário', value=interaction.user.name, inline=True)
        embed.add_field(name=f'{emoji_cargo} Cargo', value=cargo, inline=True)
        
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="❌ SAIR DO SERVIÇO", style=discord.ButtonStyle.red)
    async def sair_servico_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar se quem clicou é o mesmo que pediu
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem pediu pode usar este botão!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        cargo = obter_cargo_usuario(interaction.user)
        emoji_cargo = obter_emoji_cargo(cargo)
        horario = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        dados = carregar_dados()
        
        if user_id not in dados or not dados[user_id]['registros']:
            embed = discord.Embed(
                title='❌ Erro',
                description=f'{interaction.user.mention}, você não está em serviço!\nUse o botão "BATER PONTO" para entrar.',
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if dados[user_id]['registros'][-1].get('saida') is not None:
            embed = discord.Embed(
                title='❌ Erro',
                description=f'{interaction.user.mention}, você já saiu de serviço!',
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        entrada = dados[user_id]['registros'][-1]['entrada']
        dados[user_id]['registros'][-1]['saida'] = horario
        dados[user_id]['cargo'] = cargo
        
        salvar_dados(dados)
        
        try:
            entrada_dt = datetime.strptime(entrada, '%d/%m/%Y %H:%M:%S')
            saida_dt = datetime.strptime(horario, '%d/%m/%Y %H:%M:%S')
            duracao = saida_dt - entrada_dt
            horas = duracao.seconds // 3600
            minutos = (duracao.seconds % 3600) // 60
        except:
            horas = 0
            minutos = 0

        embed = discord.Embed(
            title=f'✅ Saída Registrada {emoji_cargo}',
            description=f'{interaction.user.mention} saiu de serviço',
            color=obter_cor_cargo(cargo)
        )
        embed.add_field(name='⏱️ Entrada', value=entrada, inline=True)
        embed.add_field(name='⏹️ Saída', value=horario, inline=True)
        embed.add_field(name='⏳ Tempo de Serviço', value=f'{horas}h {minutos}min', inline=False)
        embed.add_field(name=f'{emoji_cargo} Cargo', value=cargo, inline=False)
        
        await interaction.response.send_message(embed=embed)

# ===== EVENTOS =====
@bot.event
async def on_ready():
    print(f'{bot.user} está online!')
    print('------')

# ===== COMANDOS DE BATE-PONTO =====
@bot.command(name='bater_ponto')
async def bater_ponto(ctx):
    """Mostra botões para bater ponto ou sair de serviço"""
    view = BaterPontoView(ctx)
    
    embed = discord.Embed(
        title='🕐 Bate-Ponto',
        description='Escolha uma ação:',
        color=discord.Color.blue()
    )
    embed.add_field(name='✅ BATER PONTO', value='Clique para entrar em serviço', inline=False)
    embed.add_field(name='❌ SAIR DO SERVIÇO', value='Clique para sair de serviço', inline=False)
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='sair_servico')
async def sair_servico(ctx):
    """Alias para o comando bater_ponto (mostra botões)"""
    view = BaterPontoView(ctx)
    
    embed = discord.Embed(
        title='🕐 Bate-Ponto',
        description='Escolha uma ação:',
        color=discord.Color.blue()
    )
    embed.add_field(name='✅ BATER PONTO', value='Clique para entrar em serviço', inline=False)
    embed.add_field(name='❌ SAIR DO SERVIÇO', value='Clique para sair de serviço', inline=False)
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='meu_bate_ponto')
async def meu_bate_ponto(ctx):
    """Mostra histórico de bate-ponto do usuário"""
    user_id = str(ctx.author.id)
    dados = carregar_dados()
    
    if user_id not in dados or not dados[user_id]['registros']:
        embed = discord.Embed(
            title='📋 Histórico',
            description=f'{ctx.author.mention}, você não tem registros de bate-ponto.',
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = dados[user_id]
    registros = user_data['registros']
    cargo = user_data.get("cargo", "Sem cargo")
    emoji_cargo = obter_emoji_cargo(cargo)
    
    embed = discord.Embed(
        title=f'📋 Seu Histórico {emoji_cargo}',
        description=f'**Usuário:** {ctx.author.name}\n**Cargo:** {cargo}',
        color=obter_cor_cargo(cargo)
    )
    
    for i, reg in enumerate(registros[-10:], 1):
        entrada = reg['entrada']
        saida = reg['saida'] if reg['saida'] else '⏳ Em serviço'
        
        if reg['saida']:
            try:
                entrada_dt = datetime.strptime(entrada, '%d/%m/%Y %H:%M:%S')
                saida_dt = datetime.strptime(reg['saida'], '%d/%m/%Y %H:%M:%S')
                duracao = saida_dt - entrada_dt
                horas = duracao.seconds // 3600
                minutos = (duracao.seconds % 3600) // 60
                duracao_text = f'{horas}h {minutos}min'
            except:
                duracao_text = "N/A"
        else:
            duracao_text = "Em serviço"
        
        embed.add_field(
            name=f'#{len(registros) - 10 + i}',
            value=f'**Entrada:** {entrada}\n**Saída:** {saida}\n**Duração:** {duracao_text}',
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='relatorio_ponto')
@commands.has_permissions(administrator=True)
async def relatorio_ponto(ctx):
    """Mostra relatório de todos os bate-pontos ordenado por hierarquia"""
    dados = carregar_dados()
    
    if not dados:
        embed = discord.Embed(
            title='📊 Relatório',
            description='Nenhum registro de bate-ponto encontrado.',
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title='📊 Relatório Geral de Bate-Pontos',
        color=discord.Color.purple()
    )
    
    usuarios_ordenados = sorted(
        dados.items(),
        key=lambda x: next((i for i, (cargo, _, _) in enumerate(HIERARQUIA_CARGOS) if cargo == x[1].get('cargo', 'Sem cargo')), len(HIERARQUIA_CARGOS))
    )
    
    for user_id, user_data in usuarios_ordenados:
        total_registros = len(user_data['registros'])
        ultimo_registro = user_data['registros'][-1] if user_data['registros'] else None
        cargo = user_data.get('cargo', 'Sem cargo')
        emoji_cargo = obter_emoji_cargo(cargo)
        
        status = '✅ Saiu' if ultimo_registro and ultimo_registro.get('saida') else '🔴 Em Serviço'
        
        embed.add_field(
            name=f"{emoji_cargo} {user_data['nome']} - {cargo}",
            value=f"Total de registros: {total_registros}\nStatus: {status}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='relatorio_por_cargo')
@commands.has_permissions(administrator=True)
async def relatorio_por_cargo(ctx):
    """Mostra relatório agrupado por cargo (hierarquia respeitada)"""
    dados = carregar_dados()
    
    if not dados:
        embed = discord.Embed(
            title='📊 Relatório',
            description='Nenhum registro de bate-ponto encontrado.',
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return
    
    por_cargo = {cargo: [] for cargo, _, _ in HIERARQUIA_CARGOS}
    
    for user_id, user_data in dados.items():
        cargo = user_data.get('cargo', 'Sem cargo')
        if cargo in por_cargo:
            por_cargo[cargo].append(user_data)
    
    embed = discord.Embed(
        title='📊 Relatório por Cargo (Hierarquia)',
        color=discord.Color.purple()
    )
    
    for cargo, emoji, cor in HIERARQUIA_CARGOS:
        usuarios = por_cargo.get(cargo, [])
        if not usuarios:
            continue
        
        em_servico = 0
        total_usuarios = len(usuarios)
        
        for user_data in usuarios:
            registros = user_data['registros']
            if registros and registros[-1].get('saida') is None:
                em_servico += 1
        
        info = f"**Total:** {total_usuarios}\n**Em Serviço:** {em_servico}\n**Saíram:** {total_usuarios - em_servico}"
        embed.add_field(name=f"{emoji} {cargo}", value=info, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='oficiais_em_servico')
async def oficiais_em_servico(ctx):
    """Mostra quem está em serviço no momento"""
    dados = carregar_dados()
    
    em_servico = []
    for user_id, user_data in dados.items():
        registros = user_data['registros']
        if registros and registros[-1].get('saida') is None:
            em_servico.append(user_data)
    
    if not em_servico:
        embed = discord.Embed(
            title='🔴 Em Serviço',
            description='Ninguém está em serviço no momento.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    em_servico_ordenado = sorted(
        em_servico,
        key=lambda x: next((i for i, (cargo, _, _) in enumerate(HIERARQUIA_CARGOS) if cargo == x.get('cargo', 'Sem cargo')), len(HIERARQUIA_CARGOS))
    )
    
    embed = discord.Embed(
        title=f'🔴 Oficiais em Serviço ({len(em_servico_ordenado)})',
        color=discord.Color.green()
    )
    
    for user_data in em_servico_ordenado:
        cargo = user_data.get('cargo', 'Sem cargo')
        emoji_cargo = obter_emoji_cargo(cargo)
        
        registros = user_data['registros']
        entrada = registros[-1]['entrada']
        
        embed.add_field(
            name=f"{emoji_cargo} {user_data['nome']}",
            value=f"**Cargo:** {cargo}\n**Entrada:** {entrada}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ===== COMANDOS UTILITÁRIOS =====
@bot.command(name='ping')
async def ping(ctx):
    """Mostra a latência do bot"""
    embed = discord.Embed(
        title='🏓 Pong!',
        description=f'Latência: {round(bot.latency * 1000)}ms',
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='ajuda')
async def ajuda(ctx):
    """Mostra lista de comandos disponíveis"""
    embed = discord.Embed(
        title='📋 Comandos Disponíveis',
        description='Bot de Bate-Ponto - Polícia Militar',
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name='**🕐 Bate-Ponto**',
        value=
        '`!bater_ponto` - Mostra botões para entrar/sair de serviço\n'
        '`!meu_bate_ponto` - Mostra seu histórico\n'
        '`!oficiais_em_servico` - Lista quem está em serviço',
        inline=False
    )
    
    embed.add_field(
        name='**🛡️ Comandos Admin**',
        value=
        '`!relatorio_ponto` - Relatório geral (admin)\n'
        '`!relatorio_por_cargo` - Relatório por cargo (admin)',
        inline=False
    )
    
    embed.add_field(
        name='**⚙️ Utilitários**',
        value=
        '`!ping` - Mostra latência do bot\n'
        '`!ajuda` - Mostra esta mensagem\n'
        '`!cargos` - Mostra a hierarquia',
        inline=False
    )
    
    embed.set_footer(text='Clique nos botões para entrar e sair de serviço!')
    
    await ctx.send(embed=embed)

@bot.command(name='cargos')
async def cargos(ctx):
    """Mostra todos os cargos da hierarquia"""
    embed = discord.Embed(
        title='🎖️ Hierarquia de Cargos',
        description='Estrutura da Polícia Militar',
        color=discord.Color.gold()
    )
    
    cargos_info = [
        ("🎖️", "Coronel"),
        ("🎖️", "Tenente Coronel"),
        ("⭐", "Major"),
        ("⭐", "Capitão"),
        ("🔶", "1º Tenente"),
        ("🔶", "2º Tenente"),
        ("◽", "Aspirante Oficial"),
        ("◾", "Sub Tenente"),
        ("▪️", "1º Sargento"),
        ("▪️", "2º Sargento"),
        ("▪️", "3º Sargento"),
        ("📍", "Cabo"),
        ("🔵", "Soldado"),
        ("⚪", "Recruta"),
    ]
    
    for emoji, cargo in cargos_info:
        embed.add_field(name=f"{emoji} {cargo}", value="", inline=True)
    
    await ctx.send(embed=embed)

# Executar o bot
bot.run(TOKEN)
