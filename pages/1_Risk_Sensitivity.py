# --- BAR CHART GENERATION ---
fig = go.Figure()

x_labels = ['Status Quo', 'With Faura']
y_values = [metrics['sq_profit'], metrics['faura_profit']]
colors = ['#EF553B', '#4B604D'] # Red / Green

fig.add_trace(go.Bar(
    x=x_labels,
    y=y_values,
    marker_color=colors,
    text=[f"${val:,.0f}" for val in y_values],
    textposition='outside',             # <--- CHANGED: Puts text on top
    textfont=dict(size=22, color='#333333'), # <--- CHANGED: Big and dark text
    cliponaxis=False                    # <--- CHANGED: Prevents text clipping
))

# Calculate Delta for Annotation
delta = metrics['faura_profit'] - metrics['sq_profit']
text_color = "green" if delta > 0 else "red"
sign = "+" if delta > 0 else ""

# Calculate dynamic Y-axis range to ensure text fits
max_val = max(max(y_values), 0)
min_val = min(min(y_values), 0)
range_buffer = (max_val - min_val) * 0.2 if max_val != min_val else max_val * 0.2

fig.add_annotation(
    x=1, # Index of 'With Faura'
    y=metrics['faura_profit'],
    text=f"<b>{sign}${delta:,.0f}</b>",
    showarrow=True,
    arrowhead=2,
    ax=0,
    ay=-60, # Moved arrow higher up to clear the new large labels
    font=dict(size=24, color=text_color)
)

fig.update_layout(
    title=dict(text="Net Profit Comparison", font=dict(size=24)),
    yaxis=dict(
        title="Net Profit ($)", 
        title_font=dict(size=18),
        # Manually set range to give 'outside' text headroom
        range=[min_val - (range_buffer/2), max_val + range_buffer] 
    ),
    xaxis=dict(tickfont=dict(size=18)),
    template="plotly_white",
    height=500,
    showlegend=False,
    margin=dict(t=80) # Add top margin for the annotation
)

st.plotly_chart(fig, use_container_width=True)