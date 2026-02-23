Shader "Hidden/AlphaKeyMagenta"
{
    Properties
    {
        _MainTex ("Main", 2D) = "white" {}
        _GMax ("Max Green (key)", Range(0,1)) = 0.05
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            ZTest Always Cull Off ZWrite Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float _GMax;

            struct appdata { float4 vertex:POSITION; float2 uv:TEXCOORD0; };
            struct v2f { float2 uv:TEXCOORD0; float4 vertex:SV_POSITION; };

            v2f vert(appdata v){ v2f o; o.vertex=UnityObjectToClipPos(v.vertex); o.uv=v.uv; return o; }

            fixed4 frag(v2f i) : SV_Target
            {
                fixed4 c = tex2D(_MainTex, i.uv);

                // fundo magenta => G ~ 0
                float a = (c.g <= _GMax) ? 0.0 : 1.0;

                return fixed4(c.rgb, a);
            }
            ENDHLSL
        }
    }
}