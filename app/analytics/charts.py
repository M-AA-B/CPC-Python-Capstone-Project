"""TODO: Implement charts for analytics."""
"""Plotly charts for the S2 analytics dashboard."""

import plotly.graph_objects as go


def build_monthly_chart(monthly_totals):
    """Show recorded emissions by month."""
    if not monthly_totals:
        return None

    figure = go.Figure(
        data=[
            go.Bar(
                x=[item["month"] for item in monthly_totals],
                y=[
                    item["total_emissions"]
                    for item in monthly_totals
                ],
                marker_color="#176749",
                hovertemplate=(
                    "%{x}<br>"
                    "%{y:,.2f} kg CO₂e"
                    "<extra></extra>"
                ),
            )
        ]
    )

    figure.update_layout(
        xaxis_title="Activity month",
        yaxis_title="Emissions (kg CO₂e)",
        template="plotly_white",
        margin=dict(l=60, r=20, t=30, b=60),
        height=350,
    )

    # Show only months with records, without assuming missing
    # months have zero emissions.
    figure.update_xaxes(type="category")
    figure.update_yaxes(rangemode="tozero")

    return figure.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"responsive": True, "displaylogo": False},
    )


def build_category_chart(category_totals):
    """Compare recorded emissions across categories."""
    if not category_totals:
        return None

    figure = go.Figure(
        data=[
            go.Bar(
                x=[item["category"] for item in category_totals],
                y=[
                    item["total_emissions"]
                    for item in category_totals
                ],
                marker_color="#2878a0",
                hovertemplate=(
                    "%{x}<br>"
                    "%{y:,.2f} kg CO₂e"
                    "<extra></extra>"
                ),
            )
        ]
    )

    figure.update_layout(
        xaxis_title="Emission category",
        yaxis_title="Emissions (kg CO₂e)",
        template="plotly_white",
        margin=dict(l=60, r=20, t=30, b=60),
        height=350,
    )

    figure.update_xaxes(type="category")
    figure.update_yaxes(rangemode="tozero")

    return figure.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"responsive": True, "displaylogo": False},
    )