import plotly.graph_objects as go

def generar_grafico_donut(porcentaje: int):
    """
    Recibe un porcentaje, evalúa el color/mensaje y devuelve 
    la figura de Plotly y el mensaje.
    """
    if porcentaje < 50:
        color_grafico = "#FF4B4B"
        mensaje = "Contradicción o Ausencia"
    elif porcentaje < 85:
        color_grafico = "#FFAA00"
        mensaje = "Coherencia Parcial"
    else:
        color_grafico = "#00C853"
        mensaje = "Alineación"

    fig = go.Figure(data=[go.Pie(
        values=[porcentaje, 100 - porcentaje],
        labels=["Coherencia", "Divergencia"],
        hole=0.7,
        marker_colors=[color_grafico, "#E5E5E6"],
        textinfo='none',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=250,
        annotations=[dict(text=f"{porcentaje}%", x=0.5, y=0.5, font_size=40, showarrow=False, font=dict(color=color_grafico))]
    )
    
    return fig, mensaje