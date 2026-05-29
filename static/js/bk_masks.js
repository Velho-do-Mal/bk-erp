/**
 * BK ERP — Máscaras de entrada (Vanilla JS, sem dependências)
 */
function maskCPF(v){v=v.replace(/\D/g,'').slice(0,11);if(v.length>9)return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/,'$1.$2.$3-$4');if(v.length>6)return v.replace(/(\d{3})(\d{3})(\d{0,3})/,'$1.$2.$3');if(v.length>3)return v.replace(/(\d{3})(\d{0,3})/,'$1.$2');return v;}
function maskCNPJ(v){v=v.replace(/\D/g,'').slice(0,14);if(v.length>12)return v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,'$1.$2.$3/$4-$5');if(v.length>8)return v.replace(/(\d{2})(\d{3})(\d{3})(\d{0,4})/,'$1.$2.$3/$4');if(v.length>5)return v.replace(/(\d{2})(\d{3})(\d{0,3})/,'$1.$2.$3');if(v.length>2)return v.replace(/(\d{2})(\d{0,3})/,'$1.$2');return v;}
function maskCPFouCNPJ(v){const d=v.replace(/\D/g,'');return d.length<=11?maskCPF(d):maskCNPJ(d);}
function maskTelefone(v){v=v.replace(/\D/g,'').slice(0,11);if(v.length>10)return v.replace(/(\d{2})(\d{5})(\d{4})/,'($1) $2-$3');if(v.length>6)return v.replace(/(\d{2})(\d{4,5})(\d{0,4})/,'($1) $2-$3');if(v.length>2)return v.replace(/(\d{2})(\d{0,5})/,'($1) $2');return v;}
function maskCEP(v){v=v.replace(/\D/g,'').slice(0,8);if(v.length>5)return v.replace(/(\d{5})(\d{0,3})/,'$1-$2');return v;}
function maskMoeda(v){let d=v.replace(/\D/g,'');if(!d)return'';d=d.replace(/^0+(\d)/,'$1');while(d.length<3)d='0'+d;const int=d.slice(0,-2).replace(/\B(?=(\d{3})+(?!\d))/g,'.');return int+','+d.slice(-2);}

function applyMask(input){
  const type=input.dataset.mask;
  if(input._maskBound) return;
  input._maskBound=true;
  input.addEventListener('input',function(){
    const v=this.value;
    switch(type){
      case 'cpf':       this.value=maskCPF(v); break;
      case 'cnpj':      this.value=maskCNPJ(v); break;
      case 'cpf_cnpj':  this.value=maskCPFouCNPJ(v); break;
      case 'telefone':  this.value=maskTelefone(v); break;
      case 'cep':       this.value=maskCEP(v); break;
      case 'moeda':     this.value=maskMoeda(v); break;
    }
  });
}

function initMasksIn(container){
  (container||document).querySelectorAll('[data-mask]').forEach(applyMask);
}

document.addEventListener('DOMContentLoaded',()=>initMasksIn(document));
